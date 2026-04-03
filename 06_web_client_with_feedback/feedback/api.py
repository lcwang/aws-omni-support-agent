"""
反馈系统 FastAPI 接口

集成到 05_web_client/app.py 中
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid
import logging

from .models import FeedbackRequest, FeedbackResponse
from .handlers.positive_handler import handle_positive_feedback
from .handlers.negative_handler import handle_negative_feedback
from .config import validate_config, get_config_summary

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 验证配置
if not validate_config():
    logger.warning("⚠️ Configuration incomplete, some features may not work")

# 打印配置摘要
logger.info(f"Configuration: {get_config_summary()}")


# ==================== FastAPI 接口 ====================

# 如果是独立运行，创建 app
# 如果集成到现有 app.py，则只需要添加路由
app = FastAPI(title="Feedback System API")


@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    提交用户反馈

    参数:
        request: 反馈请求数据

    返回:
        FeedbackResponse: 反馈处理结果
    """
    logger.info(f"[Feedback] Received {request.feedback_type} for message {request.message_id}")

    try:
        # 生成反馈 ID
        feedback_id = str(uuid.uuid4())

        # 根据反馈类型路由到不同的处理器
        if request.feedback_type == "thumbs_up":
            # 点赞处理
            result = await handle_positive_feedback(feedback_id, request)

        elif request.feedback_type == "thumbs_down":
            # 点踩处理
            result = await handle_negative_feedback(feedback_id, request)

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid feedback_type: {request.feedback_type}"
            )

        # 返回成功响应
        return FeedbackResponse(
            status="success",
            message=result.get('message', 'Feedback submitted successfully'),
            feedback_id=feedback_id,
            timestamp=datetime.now().isoformat()
        )

    except ValueError as e:
        # 业务逻辑错误（如数据验证失败）
        logger.error(f"[Feedback] Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # 系统错误
        logger.error(f"[Feedback] System error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.get("/api/feedback/health")
async def health_check():
    """健康检查"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "config": get_config_summary()
    })


@app.get("/api/feedback/stats")
async def get_feedback_stats():
    """
    获取反馈统计数据（简单版本）

    完整的统计分析在 analysis_tools 中实现
    """
    try:
        from operations.dynamodb_operations import get_feedback_count

        stats = {
            "total_negative_feedback": await get_feedback_count(),
            "by_category": await get_feedback_count(group_by='issue_category'),
            "by_status": await get_feedback_count(group_by='status')
        }

        return JSONResponse({
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"[Feedback] Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve stats")


# ==================== 错误处理 ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"[Feedback] Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )


# ==================== 集成到现有 app.py 的示例代码 ====================

"""
# 在 05_web_client/app.py 中添加以下代码：

from backend.api import submit_feedback, health_check, get_feedback_stats

# 添加路由
app.post("/api/feedback")(submit_feedback)
app.get("/api/feedback/health")(health_check)
app.get("/api/feedback/stats")(get_feedback_stats)

# 或者，如果想保持代码整洁，可以使用 APIRouter：

from fastapi import APIRouter
from backend import api as feedback_api

feedback_router = APIRouter(prefix="/api/feedback", tags=["feedback"])
feedback_router.post("/")(feedback_api.submit_feedback)
feedback_router.get("/health")(feedback_api.health_check)
feedback_router.get("/stats")(feedback_api.get_feedback_stats)

app.include_router(feedback_router)
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
