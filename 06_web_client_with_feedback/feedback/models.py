"""
数据模型定义
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class RAGDocument(BaseModel):
    """RAG 检索到的文档"""
    doc_id: str
    title: str
    chunk: str
    score: float = Field(ge=0.0, le=1.0)
    source_url: Optional[str] = None


class FeedbackRequest(BaseModel):
    """反馈请求模型"""
    message_id: str
    feedback_type: Literal["thumbs_up", "thumbs_down"]
    timestamp: str

    # 问答内容
    question: str
    answer: str
    interaction_type: Literal["qa", "case"] = "qa"

    # 检索详情
    retrieval_source: Literal["rag", "llm_generated", "hybrid", "unknown"] = "unknown"
    rag_documents: List[RAGDocument] = []

    # 用户信息
    user_id: str
    session_id: str

    # 点踩特有字段
    negative_reason: Optional[Literal["hallucination", "incorrect", "incomplete", "irrelevant"]] = None
    user_comment: Optional[str] = Field(None, max_length=500)


class FeedbackResponse(BaseModel):
    """反馈响应模型"""
    status: Literal["success", "error"]
    message: str
    feedback_id: Optional[str] = None
    timestamp: str


class NegativeFeedbackRecord(BaseModel):
    """点踩反馈记录（存储到 DynamoDB）"""
    feedback_id: str
    timestamp: str

    # 问答内容
    question: str
    answer: str

    # 用户反馈
    negative_reason: str
    user_comment: Optional[str] = None

    # 检索详情
    retrieval_details: dict  # {source, rag_documents, retrieval_scores, max_score}

    # 自动分类
    issue_category: Literal["knowledge_gap", "bad_document", "weak_retrieval", "synthesis_issue", "other"]

    # 优先级和状态
    priority: Literal["high", "medium", "low"] = "medium"
    status: Literal["pending", "in_review", "resolved"] = "pending"
    frequency: int = 1

    # 处理记录
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None


class OpenSearchDocument(BaseModel):
    """OpenSearch 文档模型（用于更新）"""
    doc_id: str
    quality_score: float = 0.5
    thumbs_up_count: int = 0
    issue_count: int = 0
    last_updated: str


class ValidatedQA(BaseModel):
    """验证通过的 QA（加入 RAG）"""
    type: Literal["validated_qa"] = "validated_qa"
    question: str
    answer: str
    source: Literal["user_validated"] = "user_validated"
    quality_score: float = 1.0
    thumbs_up_count: int = 1
    validated_at: str
    question_variants: List[str] = []
