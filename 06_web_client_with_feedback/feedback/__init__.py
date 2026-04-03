"""
反馈系统模块

提供用户反馈收集、处理和分析功能
"""

from .models import FeedbackRequest, FeedbackResponse
from .api import submit_feedback, health_check, get_feedback_stats

__all__ = [
    'FeedbackRequest',
    'FeedbackResponse',
    'submit_feedback',
    'health_check',
    'get_feedback_stats',
]

__version__ = '1.0.0'
