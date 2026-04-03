"""
反馈处理器
"""

from .positive_handler import handle_positive_feedback
from .negative_handler import handle_negative_feedback

__all__ = ['handle_positive_feedback', 'handle_negative_feedback']
