"""
点踩反馈处理器

职责：
1. 分析差评原因
2. 自动分类问题类型
3. 存储到 DynamoDB 供分析
4. 实时标记问题文档（可选）
"""

import logging
from typing import Dict, Any
from datetime import datetime

from ..models import FeedbackRequest, NegativeFeedbackRecord
from ..operations.dynamodb_operations import store_negative_feedback
from ..operations.bedrock_kb_operations import flag_problematic_document
from ..config import ISSUE_CLASSIFICATION_RULES

logger = logging.getLogger(__name__)


async def handle_negative_feedback(feedback_id: str, request: FeedbackRequest) -> Dict[str, Any]:
    """
    处理点踩反馈

    参数:
        feedback_id: 反馈唯一 ID
        request: 反馈请求数据

    返回:
        处理结果
    """
    logger.info(f"[Negative] Processing thumbs_down for message {request.message_id}")
    logger.info(f"[Negative] Reason: {request.negative_reason}, Comment: {request.user_comment}")

    # 1. 构建检索详情
    retrieval_details = {
        "source": request.retrieval_source,
        "rag_documents": [doc.dict() for doc in request.rag_documents],
        "retrieval_scores": [doc.score for doc in request.rag_documents],
        "max_score": max([doc.score for doc in request.rag_documents], default=0.0)
    }

    # 2. 自动分类问题类型
    issue_category = _classify_issue(request, retrieval_details)
    logger.info(f"[Negative] Classified as: {issue_category}")

    # 3. 确定优先级
    priority = _determine_priority(issue_category, request)

    # 4. 构建存储记录
    record = NegativeFeedbackRecord(
        feedback_id=feedback_id,
        timestamp=request.timestamp,
        question=request.question,
        answer=request.answer,
        negative_reason=request.negative_reason,
        user_comment=request.user_comment,
        retrieval_details=retrieval_details,
        issue_category=issue_category,
        priority=priority,
        status="pending",
        frequency=1
    )

    try:
        # 5. 存储到 DynamoDB
        await store_negative_feedback(record)
        logger.info(f"[Negative] Stored feedback to DynamoDB: {feedback_id}")

        # 6. 实时处理（可选）
        await _real_time_actions(issue_category, request, retrieval_details)

        return {
            "action": "stored",
            "feedback_id": feedback_id,
            "issue_category": issue_category,
            "priority": priority,
            "message": "Negative feedback stored successfully"
        }

    except Exception as e:
        logger.error(f"[Negative] Failed to process: {str(e)}")
        raise


def _classify_issue(request: FeedbackRequest, retrieval_details: Dict) -> str:
    """
    自动分类问题类型

    基于决策树逻辑
    """
    source = request.retrieval_source
    reason = request.negative_reason
    max_score = retrieval_details["max_score"]

    # 决策树
    if source == "llm_generated" and reason in ["hallucination", "incorrect"]:
        return "knowledge_gap"  # 知识库缺失

    elif source == "rag" and max_score > 0.8 and reason == "incorrect":
        return "bad_document"  # RAG 文档有问题

    elif source == "rag" and 0.5 <= max_score < 0.7:
        return "weak_retrieval"  # 检索效果差

    elif source == "hybrid" and reason == "incomplete":
        return "synthesis_issue"  # 大模型综合不好

    elif max_score < 0.5:
        return "knowledge_gap"  # 检索分数太低，也算知识缺口

    else:
        return "other"


def _determine_priority(issue_category: str, request: FeedbackRequest) -> str:
    """
    确定优先级

    基于问题类型和严重程度
    """
    # 从配置中获取默认优先级
    category_config = ISSUE_CLASSIFICATION_RULES.get(issue_category, {})
    base_priority = category_config.get('priority', 'medium')

    # 动态调整：如果同一问题被多次反馈，提升优先级
    # TODO: 查询 DynamoDB 统计相同问题的频率
    # if frequency > 3:
    #     return 'high'

    return base_priority


async def _real_time_actions(issue_category: str, request: FeedbackRequest, retrieval_details: Dict):
    """
    实时处理动作（可选）

    根据问题类型执行不同动作
    """
    try:
        if issue_category == "knowledge_gap":
            # 知识缺口：记录到待补充列表
            await _flag_knowledge_gap(request.question)

        elif issue_category == "bad_document":
            # 文档质量问题：标记问题文档
            await _flag_bad_documents(request.rag_documents)

        elif issue_category == "weak_retrieval":
            # 检索效果差：记录供分析
            logger.info(f"[Negative] Weak retrieval detected, storing for analysis")

    except Exception as e:
        # 实时处理失败不应该影响主流程
        logger.error(f"[Negative] Real-time action failed: {str(e)}")


async def _flag_knowledge_gap(question: str):
    """
    标记知识缺口

    记录到 DynamoDB 的待补充列表
    """
    logger.info(f"[Negative] Flagging knowledge gap: {question[:50]}...")

    # TODO: 实现待补充文档的跟踪
    # - 检查是否已存在
    # - 如果存在，增加频率计数
    # - 如果不存在，新建记录
    pass


async def _flag_bad_documents(rag_documents: list):
    """
    标记问题文档

    更新 OpenSearch 中的 issue_count
    """
    if not rag_documents:
        return

    logger.info(f"[Negative] Flagging {len(rag_documents)} problematic documents")

    try:
        for doc in rag_documents:
            await flag_problematic_document(doc.doc_id)

        logger.info(f"[Negative] Flagged documents successfully")

    except Exception as e:
        logger.error(f"[Negative] Failed to flag documents: {str(e)}")
        # 不抛出异常，允许主流程继续
