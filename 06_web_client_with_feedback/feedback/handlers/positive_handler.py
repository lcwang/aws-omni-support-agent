"""
点赞反馈处理器

职责：
1. 判断答案来源（RAG vs LLM）
2. RAG 召回：提升文档权重
3. LLM 生成：新增到 RAG 知识库
4. 混合模式：提取精华加入 RAG
"""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

from ..models import FeedbackRequest
from ..operations.bedrock_kb_operations import (
    boost_document_priority,
    add_validated_qa_to_kb,
    check_similarity
)

logger = logging.getLogger(__name__)


async def handle_positive_feedback(feedback_id: str, request: FeedbackRequest) -> Dict[str, Any]:
    """
    处理点赞反馈

    参数:
        feedback_id: 反馈唯一 ID
        request: 反馈请求数据

    返回:
        处理结果
    """
    logger.info(f"[Positive] Processing thumbs_up for message {request.message_id}")

    # 1. 过滤：只处理 QA 类型
    if request.interaction_type != "qa":
        logger.info(f"[Positive] Skipped: interaction_type={request.interaction_type} (only QA eligible)")
        return {
            "action": "skipped",
            "reason": "Case operations not eligible for RAG",
            "message": "Feedback received but not processed"
        }

    # 2. 根据来源分类处理
    source = request.retrieval_source

    # 如果来源是 unknown，根据是否有 rag_documents 推断
    if source == "unknown":
        if request.rag_documents and len(request.rag_documents) > 0:
            logger.info(f"[Positive] Unknown source but has rag_documents, treating as RAG")
            source = "rag"
        else:
            logger.info(f"[Positive] Unknown source without rag_documents, treating as LLM generated")
            source = "llm_generated"

    if source == "rag":
        # 场景 A: RAG 召回的答案被点赞
        return await _handle_rag_thumbs_up(feedback_id, request)

    elif source == "llm_generated":
        # 场景 B: 纯大模型生成的答案被点赞
        return await _handle_llm_thumbs_up(feedback_id, request)

    elif source == "hybrid":
        # 场景 C: RAG + 大模型加工的答案被点赞
        return await _handle_hybrid_thumbs_up(feedback_id, request)

    else:
        # 不应该到达这里
        logger.warning(f"[Positive] Unexpected retrieval_source: {source}")
        return {
            "action": "skipped",
            "reason": f"Unexpected retrieval_source: {source}",
            "message": "Feedback received but not processed"
        }


async def _handle_rag_thumbs_up(feedback_id: str, request: FeedbackRequest) -> Dict[str, Any]:
    """
    处理 RAG 召回的点赞

    策略：只记录用户满意度，不上传（内容已在 KB 中）

    说明：
    - RAG 召回的内容已经在 Knowledge Base 中
    - 点赞表示用户对检索质量满意
    - 无需重复添加到 KB
    - Bedrock KB 不支持直接修改文档权重
    """
    logger.info(f"[Positive] RAG thumbs_up: recording user satisfaction (no upload needed)")

    if not request.rag_documents:
        logger.warning(f"[Positive] No RAG documents found despite source=rag")

    # 可选：记录到 DynamoDB 的高质量文档表
    # 供运营团队分析哪些文档质量高
    # await record_high_quality_documents(request.rag_documents)

    return {
        "action": "recorded",
        "document_count": len(request.rag_documents) if request.rag_documents else 0,
        "message": "Feedback recorded (content already in Knowledge Base)"
    }


async def _add_qa_to_kb_background(question: str, answer: str, timestamp: str):
    """
    后台任务：异步添加 QA 到 Knowledge Base

    Args:
        question: 问题
        answer: 答案
        timestamp: 时间戳
    """
    try:
        logger.info(f"[Background] Starting to add QA to KB: {question[:50]}...")

        # 检查相似度，避免重复
        similar_docs = await check_similarity(
            question=question,
            threshold=0.95
        )

        if similar_docs:
            logger.info(f"[Background] Found {len(similar_docs)} similar documents, skipping duplicate")
            return

        # 添加到 RAG
        new_doc_id = await add_validated_qa_to_kb(
            question=question,
            answer=answer,
            validated_at=timestamp
        )

        logger.info(f"[Background] Successfully added QA to RAG: {new_doc_id}")

    except Exception as e:
        logger.error(f"[Background] Failed to add QA to RAG: {str(e)}", exc_info=True)


async def _handle_llm_thumbs_up(feedback_id: str, request: FeedbackRequest) -> Dict[str, Any]:
    """
    处理纯 LLM 生成的点赞

    策略：这是新知识，异步加入 RAG（不阻塞响应）
    """
    logger.info(f"[Positive] LLM thumbs_up: scheduling background task to add to RAG")

    try:
        # 启动后台任务（fire-and-forget）
        asyncio.create_task(
            _add_qa_to_kb_background(
                question=request.question,
                answer=request.answer,
                timestamp=request.timestamp
            )
        )

        # 立即返回，不等待上传完成
        return {
            "action": "add_to_rag_async",
            "message": "Feedback received, content will be added to Knowledge Base in background"
        }

    except Exception as e:
        logger.error(f"[Positive] Failed to schedule background task: {str(e)}")
        raise


async def _handle_hybrid_thumbs_up(feedback_id: str, request: FeedbackRequest) -> Dict[str, Any]:
    """
    处理混合模式的点赞

    策略（简化版）：只记录，不上传
    - RAG 召回 + LLM 合成
    - 原始内容已在 KB 中
    - 合成答案虽然可能更好，但为避免重复，暂不上传
    - 如需精华版，可由运营团队手动审核后添加

    TODO: 如果未来需要"精华版"，可以：
    1. 判断合成答案是否显著优于原片段
    2. 如果是，上传为"精华版"（标记为 user_validated + llm_enhanced）
    """
    logger.info(f"[Positive] Hybrid thumbs_up: recording satisfaction (no upload to avoid duplication)")

    return {
        "action": "recorded",
        "document_count": len(request.rag_documents) if request.rag_documents else 0,
        "message": "Feedback recorded (original content already in Knowledge Base)"
    }


async def _is_significantly_better(original_chunks: list, synthesized_answer: str) -> bool:
    """
    判断合成答案是否显著优于原始片段

    简单版本：比较长度和结构
    完整版本：使用 LLM 评估
    """
    # 简单策略：如果答案明显更长且结构化更好，视为改进
    original_length = sum(len(chunk) for chunk in original_chunks)
    answer_length = len(synthesized_answer)

    # 长度增加 > 30% 且包含结构化标记（如代码块、列表）
    length_improvement = answer_length > original_length * 1.3
    has_structure = any(marker in synthesized_answer for marker in ['```', '1.', '- ', '##'])

    return length_improvement and has_structure

    # TODO: 完整版本 - 使用 LLM 评估质量
    # from operations.bedrock_operations import evaluate_answer_quality
    # quality_score = await evaluate_answer_quality(original_chunks, synthesized_answer)
    # return quality_score > 0.8
