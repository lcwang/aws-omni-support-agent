"""
DynamoDB 操作

职责：
1. 存储点踩反馈
2. 查询反馈统计
3. 更新反馈状态
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

from ..models import NegativeFeedbackRecord
from ..config import (
    AWS_REGION,
    DYNAMODB_TABLE_NAME,
    DYNAMODB_GSI_NAME
)

logger = logging.getLogger(__name__)

# 初始化 DynamoDB 客户端
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)


# ==================== 存储反馈 ====================

async def store_negative_feedback(record: NegativeFeedbackRecord) -> bool:
    """
    存储点踩反馈到 DynamoDB

    参数:
        record: 反馈记录

    返回:
        是否成功
    """
    logger.info(f"[DynamoDB] Storing negative feedback: {record.feedback_id}")

    try:
        # 检查是否已存在相同问题的反馈
        existing_feedback = await _find_similar_feedback(record.question)

        if existing_feedback:
            # 更新频率
            logger.info(f"[DynamoDB] Found similar feedback, updating frequency")
            await _update_feedback_frequency(existing_feedback['feedback_id'])
        else:
            # 新建记录
            item = record.dict()

            # 转换嵌套对象为 DynamoDB 格式
            item['retrieval_details'] = _serialize_retrieval_details(item['retrieval_details'])

            response = table.put_item(Item=item)

            logger.info(f"[DynamoDB] Stored feedback successfully: {record.feedback_id}")

        return True

    except ClientError as e:
        logger.error(f"[DynamoDB] Failed to store feedback: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        logger.error(f"[DynamoDB] Failed to store feedback: {str(e)}")
        raise


# ==================== 查询反馈 ====================

async def get_feedback_count(group_by: Optional[str] = None) -> Dict[str, Any]:
    """
    获取反馈统计

    参数:
        group_by: 分组字段（'issue_category' | 'status' | None）

    返回:
        统计结果
    """
    logger.info(f"[DynamoDB] Getting feedback count, group_by={group_by}")

    try:
        if group_by == 'issue_category':
            # 按问题类型统计
            return await _count_by_issue_category()

        elif group_by == 'status':
            # 按状态统计
            return await _count_by_status()

        else:
            # 总数
            response = table.scan(Select='COUNT')
            return {"total": response['Count']}

    except ClientError as e:
        logger.error(f"[DynamoDB] Failed to get count: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        logger.error(f"[DynamoDB] Failed to get count: {str(e)}")
        raise


async def query_feedback_by_category(
    category: str,
    status: str = "pending",
    limit: int = 100
) -> list:
    """
    按类别查询反馈

    使用 GSI: issue_category-status-index

    参数:
        category: 问题类型
        status: 状态
        limit: 返回数量

    返回:
        反馈列表
    """
    logger.info(f"[DynamoDB] Querying feedback: category={category}, status={status}")

    try:
        response = table.query(
            IndexName=DYNAMODB_GSI_NAME,
            KeyConditionExpression='issue_category = :cat AND #status = :stat',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':cat': category,
                ':stat': status
            },
            Limit=limit
        )

        items = response.get('Items', [])
        logger.info(f"[DynamoDB] Found {len(items)} feedback items")

        return items

    except ClientError as e:
        logger.error(f"[DynamoDB] Failed to query: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        logger.error(f"[DynamoDB] Failed to query: {str(e)}")
        raise


# ==================== 更新反馈 ====================

async def update_feedback_status(
    feedback_id: str,
    status: str,
    resolution_notes: Optional[str] = None
):
    """
    更新反馈状态

    参数:
        feedback_id: 反馈 ID
        status: 新状态
        resolution_notes: 处理说明
    """
    logger.info(f"[DynamoDB] Updating feedback status: {feedback_id} → {status}")

    try:
        from datetime import datetime

        update_expr = "SET #status = :status, resolved_at = :time"
        expr_attr_names = {'#status': 'status'}
        expr_attr_values = {
            ':status': status,
            ':time': datetime.now().isoformat()
        }

        if resolution_notes:
            update_expr += ", resolution_notes = :notes"
            expr_attr_values[':notes'] = resolution_notes

        response = table.update_item(
            Key={'feedback_id': feedback_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values,
            ReturnValues='ALL_NEW'
        )

        logger.info(f"[DynamoDB] Updated feedback successfully")
        return response['Attributes']

    except ClientError as e:
        logger.error(f"[DynamoDB] Failed to update: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        logger.error(f"[DynamoDB] Failed to update: {str(e)}")
        raise


# ==================== 辅助函数 ====================

async def _find_similar_feedback(question: str, time_window_hours: int = 24) -> Optional[Dict]:
    """
    查找相似的反馈（去重）

    简单版本：精确匹配问题文本
    完整版本：使用 embedding 计算相似度
    """
    from datetime import datetime, timedelta

    try:
        # 计算时间窗口
        cutoff_time = (datetime.now() - timedelta(hours=time_window_hours)).isoformat()

        # 扫描近期的反馈
        response = table.scan(
            FilterExpression='question = :q AND #timestamp > :time',
            ExpressionAttributeNames={'#timestamp': 'timestamp'},
            ExpressionAttributeValues={
                ':q': question,
                ':time': cutoff_time
            },
            Limit=1
        )

        items = response.get('Items', [])
        return items[0] if items else None

    except Exception as e:
        logger.error(f"[DynamoDB] Failed to find similar feedback: {str(e)}")
        return None


async def _update_feedback_frequency(feedback_id: str):
    """更新反馈频率（相同问题被重复反馈）"""
    try:
        response = table.update_item(
            Key={'feedback_id': feedback_id},
            UpdateExpression='SET frequency = frequency + :inc, last_reported = :time',
            ExpressionAttributeValues={
                ':inc': 1,
                ':time': datetime.now().isoformat()
            },
            ReturnValues='ALL_NEW'
        )

        new_frequency = response['Attributes']['frequency']
        logger.info(f"[DynamoDB] Updated frequency to {new_frequency}")

        # 如果频率超过阈值，提升优先级
        if new_frequency >= 3 and response['Attributes'].get('priority') != 'high':
            await _update_priority(feedback_id, 'high')

    except Exception as e:
        logger.error(f"[DynamoDB] Failed to update frequency: {str(e)}")


async def _update_priority(feedback_id: str, priority: str):
    """更新优先级"""
    try:
        table.update_item(
            Key={'feedback_id': feedback_id},
            UpdateExpression='SET priority = :p',
            ExpressionAttributeValues={':p': priority}
        )
        logger.info(f"[DynamoDB] Updated priority to {priority}")
    except Exception as e:
        logger.error(f"[DynamoDB] Failed to update priority: {str(e)}")


async def _count_by_issue_category() -> Dict[str, int]:
    """按问题类型统计"""
    try:
        response = table.scan(
            ProjectionExpression='issue_category'
        )

        items = response.get('Items', [])

        # 统计各类型数量
        counts = {}
        for item in items:
            category = item.get('issue_category', 'unknown')
            counts[category] = counts.get(category, 0) + 1

        return counts

    except Exception as e:
        logger.error(f"[DynamoDB] Failed to count by category: {str(e)}")
        return {}


async def _count_by_status() -> Dict[str, int]:
    """按状态统计"""
    try:
        response = table.scan(
            ProjectionExpression='#status',
            ExpressionAttributeNames={'#status': 'status'}
        )

        items = response.get('Items', [])

        # 统计各状态数量
        counts = {}
        for item in items:
            status = item.get('status', 'unknown')
            counts[status] = counts.get(status, 0) + 1

        return counts

    except Exception as e:
        logger.error(f"[DynamoDB] Failed to count by status: {str(e)}")
        return {}


def _serialize_retrieval_details(details: dict) -> dict:
    """序列化检索详情为 DynamoDB 兼容格式"""
    # DynamoDB 不支持空字符串和 float，需要转换

    def convert_value(v):
        """转换单个值"""
        if v == "":
            return "N/A"
        elif isinstance(v, float):
            return Decimal(str(v))  # float → Decimal
        else:
            return v

    serialized = {}

    for key, value in details.items():
        if isinstance(value, list):
            # 处理列表（如 rag_documents）
            serialized[key] = [
                {k: convert_value(v) for k, v in item.items()}
                if isinstance(item, dict) else convert_value(item)
                for item in value
            ]
        else:
            serialized[key] = convert_value(value)

    return serialized
