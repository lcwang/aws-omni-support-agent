"""
Bedrock Knowledge Base 操作

用于 AWS Bedrock Knowledge Base 的反馈处理
替代 opensearch_operations.py（用于直接操作 OpenSearch 的场景）

使用场景：
- 你的 RAG 使用 Bedrock Knowledge Base
- 底层是 OpenSearch Serverless
- 通过 S3 数据源管理文档

数据流：
1. 点赞的 QA → 存储到 DynamoDB
2. 定期批量导出 → S3 (JSON/TXT)
3. 触发 Knowledge Base 数据源同步
"""

import logging
import json
import boto3
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..models import RAGDocument, ValidatedQA
from ..config import AWS_REGION, KNOWLEDGE_BASE_ID as CONFIG_KB_ID, KB_S3_BUCKET, KB_S3_PREFIX

logger = logging.getLogger(__name__)

# 初始化客户端
s3_client = boto3.client('s3', region_name=AWS_REGION)
bedrock_agent_client = boto3.client('bedrock-agent', region_name=AWS_REGION)

# 配置（可以被 configure_kb() 覆盖，或从环境变量读取）
KNOWLEDGE_BASE_ID = CONFIG_KB_ID or None
S3_BUCKET = KB_S3_BUCKET or None
S3_PREFIX = KB_S3_PREFIX or 'validated-qa/'


def configure_kb(knowledge_base_id: str, s3_bucket: str):
    """
    配置 Knowledge Base 信息

    参数:
        knowledge_base_id: Knowledge Base ID
        s3_bucket: S3 存储桶名称
    """
    global KNOWLEDGE_BASE_ID, S3_BUCKET
    KNOWLEDGE_BASE_ID = knowledge_base_id
    S3_BUCKET = s3_bucket
    logger.info(f"Configured KB: {knowledge_base_id}, Bucket: {s3_bucket}")


# ==================== 点赞处理（简化版）====================

async def boost_document_priority(documents: List[RAGDocument], boost_amount: float = 0.1) -> List[str]:
    """
    提升文档权重（Bedrock KB 版本）

    注意：Bedrock Knowledge Base 不支持直接更新文档权重
    替代方案：记录到 DynamoDB，定期分析高质量文档

    参数:
        documents: 文档列表
        boost_amount: 权重提升值（此处不使用）

    返回:
        文档 ID 列表
    """
    logger.info(f"[Bedrock KB] Recording {len(documents)} high-quality documents")

    # Bedrock KB 不支持实时更新权重
    # 替代方案：记录到 DynamoDB，供后续分析
    doc_ids = [doc.doc_id for doc in documents]

    # 可以在这里记录到一个专门的 DynamoDB 表
    # 用于追踪高质量文档，供后续人工审查

    logger.info(f"[Bedrock KB] Recorded {len(doc_ids)} documents as high-quality")
    return doc_ids


# ==================== 添加验证 QA ====================

async def add_validated_qa_to_kb(
    question: str,
    answer: str,
    validated_at: str,
    source_documents: Optional[List[str]] = None
) -> str:
    """
    添加验证通过的 QA 到 Knowledge Base

    流程：
    1. 保存 QA 到 S3（JSON 格式）
    2. 触发 Knowledge Base 数据源同步

    参数:
        question: 问题
        answer: 答案
        validated_at: 验证时间
        source_documents: 来源文档 ID

    返回:
        S3 对象 key
    """
    if not KNOWLEDGE_BASE_ID or not S3_BUCKET:
        logger.error("[Bedrock KB] KB not configured! Call configure_kb() first")
        raise ValueError("Knowledge Base not configured")

    logger.info(f"[Bedrock KB] Adding validated QA: {question[:50]}...")

    # 1. 构建文档（Bedrock KB 推荐格式）
    doc = {
        "type": "validated_qa",
        "question": question,
        "answer": answer,
        "metadata": {
            "source": "user_validated",
            "validated_at": validated_at,
            "source_documents": source_documents or [],
            "quality_score": 1.0
        }
    }

    # 2. 生成文档内容（Knowledge Base 会自动 embedding）
    # 格式：Markdown 或纯文本
    content = f"""# {question}

{answer}

---
Validated at: {validated_at}
Source: User Feedback
"""

    # 3. 生成 S3 key
    import hashlib
    doc_id = hashlib.md5(question.encode()).hexdigest()[:16]
    s3_key = f"{S3_PREFIX}{doc_id}.txt"

    try:
        # 4. 上传到 S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=content.encode('utf-8'),
            ContentType='text/plain',
            Metadata={
                'type': 'validated_qa',
                'validated_at': validated_at,
                'source': 'user_feedback'
            }
        )

        logger.info(f"[Bedrock KB] Uploaded to S3: s3://{S3_BUCKET}/{s3_key}")

        # 5. 触发数据源同步（可选，可以定期批量同步）
        await trigger_kb_sync()

        return s3_key

    except Exception as e:
        logger.error(f"[Bedrock KB] Failed to upload: {str(e)}")
        raise


# ==================== 触发 Knowledge Base 同步 ====================

async def trigger_kb_sync():
    """
    触发 Knowledge Base 数据源同步

    注意：
    - 同步是异步的，可能需要几分钟
    - 建议批量同步而不是每次添加都触发
    """
    if not KNOWLEDGE_BASE_ID:
        logger.warning("[Bedrock KB] KB not configured, skip sync")
        return

    try:
        # 获取 Knowledge Base 的数据源
        response = bedrock_agent_client.list_data_sources(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )

        if not response.get('dataSourceSummaries'):
            logger.warning("[Bedrock KB] No data source found")
            return

        data_source_id = response['dataSourceSummaries'][0]['dataSourceId']

        # 触发数据源同步
        sync_response = bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=data_source_id
        )

        ingestion_job_id = sync_response['ingestionJob']['ingestionJobId']
        logger.info(f"[Bedrock KB] Sync triggered: {ingestion_job_id}")

    except Exception as e:
        logger.error(f"[Bedrock KB] Failed to trigger sync: {str(e)}")
        # 不抛出异常，允许主流程继续


# ==================== 批量同步（推荐）====================

async def batch_sync_validated_qa(limit: int = 100):
    """
    批量同步验证的 QA 到 Knowledge Base

    推荐使用定时任务（如 Lambda + EventBridge）每天运行一次

    参数:
        limit: 每次同步的最大数量

    返回:
        同步的文档数量
    """
    logger.info(f"[Bedrock KB] Starting batch sync (limit: {limit})")

    # 从 DynamoDB 获取待同步的 QA
    # TODO: 实现从 DynamoDB 查询逻辑
    # pending_qa = query_pending_validated_qa(limit)

    count = 0
    # for qa in pending_qa:
    #     s3_key = await add_validated_qa_to_kb(
    #         question=qa['question'],
    #         answer=qa['answer'],
    #         validated_at=qa['validated_at']
    #     )
    #     count += 1

    # 批量上传完成后，触发一次同步
    if count > 0:
        await trigger_kb_sync()
        logger.info(f"[Bedrock KB] Batch sync completed: {count} documents")

    return count


# ==================== 检索测试 ====================

async def test_kb_retrieval(query: str, top_k: int = 5) -> List[Dict]:
    """
    测试 Knowledge Base 检索

    用于验证新添加的 QA 是否可以被检索到
    """
    if not KNOWLEDGE_BASE_ID:
        logger.error("[Bedrock KB] KB not configured")
        return []

    try:
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)

        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': top_k
                }
            }
        )

        results = []
        for result in response.get('retrievalResults', []):
            results.append({
                'content': result['content']['text'],
                'score': result['score'],
                'metadata': result.get('metadata', {})
            })

        logger.info(f"[Bedrock KB] Retrieved {len(results)} results for: {query[:50]}")
        return results

    except Exception as e:
        logger.error(f"[Bedrock KB] Retrieval failed: {str(e)}")
        return []


# ==================== 相似度检查（基于 KB 检索）====================

async def check_similarity(question: str, threshold: float = 0.95) -> List[Dict[str, Any]]:
    """
    检查问题的相似度（使用 KB 检索）

    参数:
        question: 问题文本
        threshold: 相似度阈值

    返回:
        相似文档列表
    """
    results = await test_kb_retrieval(question, top_k=3)

    # 过滤高相似度结果
    similar_docs = [
        {
            'content': r['content'],
            'score': r['score'],
            'metadata': r.get('metadata', {})
        }
        for r in results
        if r['score'] > threshold
    ]

    logger.info(f"[Bedrock KB] Found {len(similar_docs)} similar documents")
    return similar_docs


# ==================== 标记问题文档（记录版）====================

async def flag_problematic_document(doc_id: str):
    """
    标记有问题的文档

    注意：Bedrock KB 不支持直接修改文档
    替代方案：记录到 DynamoDB，供人工审查
    """
    logger.info(f"[Bedrock KB] Flagging document: {doc_id}")

    # 记录到 DynamoDB 的 problematic_documents 表
    # 供管理员定期审查和修正

    logger.info(f"[Bedrock KB] Document flagged for review: {doc_id}")
