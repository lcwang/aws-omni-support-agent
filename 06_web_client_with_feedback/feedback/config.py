"""
反馈系统配置文件
"""

import os
from typing import Dict, Any

# AWS 配置
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID', '')

# DynamoDB 配置
DYNAMODB_TABLE_NAME = os.environ.get(
    'FEEDBACK_TABLE_NAME',
    'support-agent-feedback-negative'
)
DYNAMODB_GSI_NAME = 'issue_category-status-index'

# Bedrock Knowledge Base 配置（可选，仅点赞功能需要）
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', '')
KB_S3_BUCKET = os.environ.get('KB_S3_BUCKET', '')
KB_S3_PREFIX = os.environ.get('KB_S3_PREFIX', 'validated-qa/')

# Bedrock 配置（用于生成问题变体）
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-5-20250929-v1:0')
TITAN_EMBEDDING_MODEL_ID = 'amazon.titan-embed-text-v2:0'

# 权重和阈值
QUALITY_SCORE_BOOST = float(os.environ.get('QUALITY_SCORE_BOOST', '0.1'))  # 每次点赞增加的分数
SIMILARITY_THRESHOLD = float(os.environ.get('SIMILARITY_THRESHOLD', '0.95'))  # 去重阈值
CACHE_TTL = int(os.environ.get('CACHE_TTL', '300'))  # 缓存 TTL（秒）

# 问题分类规则
ISSUE_CLASSIFICATION_RULES: Dict[str, Any] = {
    'knowledge_gap': {
        'conditions': [
            {'retrieval_source': 'llm_generated', 'negative_reason': 'hallucination'},
            {'retrieval_source': 'llm_generated', 'negative_reason': 'incorrect'},
            {'max_score': ('lt', 0.5)}
        ],
        'priority': 'high'
    },
    'bad_document': {
        'conditions': [
            {'retrieval_source': 'rag', 'max_score': ('gt', 0.8), 'negative_reason': 'incorrect'}
        ],
        'priority': 'high'
    },
    'weak_retrieval': {
        'conditions': [
            {'retrieval_source': 'rag', 'max_score': ('between', 0.5, 0.7)}
        ],
        'priority': 'medium'
    },
    'synthesis_issue': {
        'conditions': [
            {'retrieval_source': 'hybrid', 'negative_reason': 'incomplete'}
        ],
        'priority': 'medium'
    }
}

# 日志配置
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')


def validate_config() -> bool:
    """
    验证必要的配置是否存在

    必需配置：
    - DynamoDB 表名（用于存储点踩数据）

    可选配置：
    - Knowledge Base ID 和 S3 Bucket（仅点赞更新 RAG 需要）
    """
    warnings = []
    errors = []

    # 必需配置检查
    if not DYNAMODB_TABLE_NAME:
        errors.append("DYNAMODB_TABLE_NAME not set")

    # 可选配置警告
    if not KNOWLEDGE_BASE_ID or not KB_S3_BUCKET:
        warnings.append("Knowledge Base not configured (thumbs_up RAG update disabled)")

    if not AWS_ACCOUNT_ID:
        warnings.append("AWS_ACCOUNT_ID not set (can be auto-detected)")

    if warnings:
        print(f"⚠️ Configuration warnings: {', '.join(warnings)}")

    if errors:
        print(f"❌ Configuration errors: {', '.join(errors)}")
        return False

    return True


def get_config_summary() -> Dict[str, Any]:
    """获取配置摘要（隐藏敏感信息）"""
    return {
        'aws_region': AWS_REGION,
        'dynamodb_table': DYNAMODB_TABLE_NAME,
        'knowledge_base_id': KNOWLEDGE_BASE_ID if KNOWLEDGE_BASE_ID else 'NOT_SET',
        'kb_s3_bucket': KB_S3_BUCKET if KB_S3_BUCKET else 'NOT_SET',
        'bedrock_model': BEDROCK_MODEL_ID,
        'quality_score_boost': QUALITY_SCORE_BOOST,
        'similarity_threshold': SIMILARITY_THRESHOLD,
        'thumbs_up_rag_update': 'ENABLED' if KNOWLEDGE_BASE_ID and KB_S3_BUCKET else 'DISABLED'
    }
