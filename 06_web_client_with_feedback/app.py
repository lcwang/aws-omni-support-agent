"""
AWS AgentCore Runtime Web Client - FastAPI Backend
支持流式输出的 Web 聊天界面
"""

import boto3
import json
import os
import pickle
import uuid
import base64
import sys
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from boto3.session import Session
from pathlib import Path
import asyncio
from typing import AsyncGenerator, List, Dict

# 导入反馈系统（现在可以直接导入，不需要 sys.path.append）
# 注意：Knowledge Base 配置通过环境变量传入：
#   export KNOWLEDGE_BASE_ID="your-kb-id"
#   export KB_S3_BUCKET="your-s3-bucket"
try:
    from feedback import FeedbackRequest, submit_feedback, health_check, get_feedback_stats
    FEEDBACK_ENABLED = True
    print("✅ Feedback system enabled")
except ImportError as e:
    print(f"⚠️ Warning: Feedback system not available: {e}")
    FEEDBACK_ENABLED = False

app = FastAPI(title="AWS Support Agent Web Client")

# 挂载静态文件和模板
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 全局配置
REGION = os.environ.get('AWS_REGION', 'us-east-1')
AGENT_ARN = None


def get_agent_arn():
    """获取 Agent ARN（从 pickle 文件或环境变量）"""
    global AGENT_ARN

    if AGENT_ARN:
        return AGENT_ARN

    # 尝试从 pickle 文件读取
    pickle_path = BASE_DIR.parent / 'launch_result.pkl'
    try:
        with open(pickle_path, 'rb') as f:
            launch_result = pickle.load(f)
        AGENT_ARN = launch_result.agent_arn
        return AGENT_ARN
    except FileNotFoundError:
        pass

    # 从环境变量读取
    AGENT_ARN = os.environ.get('AGENT_ARN')

    # 如果是测试模式，允许不配置 Agent ARN
    if not AGENT_ARN and os.environ.get('TEST_MODE') != '1':
        raise ValueError(
            "Agent ARN not found. Please either:\n"
            "1. Ensure launch_result.pkl exists in parent directory, or\n"
            "2. Set AGENT_ARN environment variable, or\n"
            "3. Set TEST_MODE=1 to test UI without backend"
        )

    return AGENT_ARN


def upload_attachments_to_support(attachments: List[Dict]) -> str:
    """
    上传附件到 AWS Support，返回 attachmentSetId

    Args:
        attachments: 附件列表 [{"name": "file.pdf", "data": "base64...", "type": "..."}]

    Returns:
        attachmentSetId: AWS Support 的附件集 ID

    AWS Support 限制:
    - 单个文件最大 5MB
    - 所有附件总大小最大 25MB
    """
    if not attachments:
        return None

    try:
        # 验证附件大小
        MAX_SINGLE_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        MAX_TOTAL_SIZE = 25 * 1024 * 1024  # 25MB

        total_size = 0
        for att in attachments:
            # 解码 base64 获取实际大小
            file_data = base64.b64decode(att['data'])
            file_size = len(file_data)
            total_size += file_size

            if file_size > MAX_SINGLE_FILE_SIZE:
                raise ValueError(
                    f"文件 '{att['name']}' 大小 {file_size / 1024 / 1024:.2f}MB 超过 5MB 限制"
                )

        if total_size > MAX_TOTAL_SIZE:
            raise ValueError(
                f"附件总大小 {total_size / 1024 / 1024:.2f}MB 超过 25MB 限制"
            )

        support_client = boto3.client('support', region_name='us-east-1')

        # 准备附件数据
        attachment_data = [
            {
                'fileName': att['name'],
                'data': base64.b64decode(att['data'])  # AWS API 需要 bytes，不是 base64 string
            }
            for att in attachments
        ]

        # 调用 AWS Support API 上传附件
        response = support_client.add_attachments_to_set(
            attachments=attachment_data
        )

        attachment_set_id = response['attachmentSetId']
        print(f"✅ Uploaded {len(attachments)} attachment(s), attachmentSetId: {attachment_set_id}")

        return attachment_set_id

    except Exception as e:
        print(f"❌ Failed to upload attachments: {e}")
        raise


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主页面"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """健康检查接口"""
    try:
        agent_arn = get_agent_arn()
        return {
            "status": "healthy",
            "agent_arn": agent_arn,
            "region": REGION
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def stream_agent_response(prompt: str, attachments: list = None, user_id: str = None, session_id: str = None) -> AsyncGenerator[str, None]:
    """流式调用 Agent 并生成响应"""
    try:
        agent_arn = get_agent_arn()

        if attachments is None:
            attachments = []

        # 测试模式 - 返回模拟响应
        if os.environ.get('TEST_MODE') == '1' or not agent_arn:
            test_response = f"""收到你的消息：{prompt}

这是一个测试响应。由于当前处于测试模式，无法实际调用 AWS Agent。

要启用真实的 Agent 调用，请：
1. 配置 AGENT_ARN 环境变量
2. 移除 TEST_MODE 环境变量

**支持的功能**：
- 查询 AWS Support Cases
- 创建新的 Support Case
- 更新 Case 信息
- 查看 Case 详情
"""
            # 模拟流式输出
            for char in test_response:
                yield f"data: {json.dumps({'content': char})}\n\n"
                await asyncio.sleep(0.02)
            yield f"data: {json.dumps({'done': True})}\n\n"
            return

        # 如果有附件，先上传到 AWS Support 获取 attachmentSetId
        attachment_set_id = None
        if attachments:
            try:
                attachment_set_id = upload_attachments_to_support(attachments)
                # 将附件信息添加到 prompt 中
                attachment_info = f"\n\n📎 已上传 {len(attachments)} 个附件:\n"
                attachment_info += "\n".join([f"- {att['name']}" for att in attachments])
                attachment_info += f"\n\nattachmentSetId: {attachment_set_id}"
                attachment_info += "\n\n请在创建 Support Case 时使用这个 attachmentSetId。"
                prompt = prompt + attachment_info
            except Exception as e:
                error_msg = f"附件上传失败: {str(e)}"
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                return

        # 完全按照 agent_client.py 的方式调用
        agentcore_client = boto3.client("bedrock-agentcore", region_name=REGION)

        # 构建 payload
        payload = {"prompt": prompt}

        # 如果提供了 user_id，添加到 payload
        if user_id:
            payload["_user_context"] = {"iam_user": user_id}

        # 构建调用参数
        invoke_params = {
            "agentRuntimeArn": agent_arn,
            "qualifier": "DEFAULT",
            "payload": json.dumps(payload)
        }

        # 如果提供了 session_id，添加到参数中（维持会话上下文）
        if session_id:
            invoke_params["runtimeSessionId"] = session_id  # 正确的参数名

        # 调用 Agent Runtime
        boto3_response = agentcore_client.invoke_agent_runtime(**invoke_params)

        # 处理流式响应（真正的流式读取）
        if "text/event-stream" in boto3_response.get("contentType", ""):
            # 使用 iter_lines() 逐行读取，避免等待全部响应
            stream = boto3_response["response"]

            # 在线程池中读取流（boto3 StreamingBody 是同步的）
            loop = asyncio.get_event_loop()
            buffer = b""
            retrieval_results = []  # Store retrieval metadata for this message

            while True:
                # 逐块读取（1KB）
                chunk = await loop.run_in_executor(None, stream.read, 1024)
                if not chunk:
                    break

                buffer += chunk

                # 处理完整的行
                while b'\n' in buffer:
                    line_bytes, buffer = buffer.split(b'\n', 1)
                    try:
                        line = line_bytes.decode('utf-8')

                        if line.startswith('data: '):
                            data_str = line[6:].strip()

                            # Try to parse as JSON (could be metadata event)
                            try:
                                data_obj = json.loads(data_str.strip('"'))

                                # Check if it's a metadata event
                                if isinstance(data_obj, dict) and data_obj.get('type') == 'metadata':
                                    retrieval_results = data_obj.get('retrieval_results', [])
                                    logger.info(f"Captured {len(retrieval_results)} retrieval results")
                                    continue  # Don't send metadata as content

                            except json.JSONDecodeError:
                                # Not JSON, treat as plain text
                                pass

                            # Regular text content
                            if data_str and data_str != '\\n':
                                # 清理转义字符
                                cleaned_data = data_str.strip('"').replace('\\n', '\n')
                                # 以 SSE 格式发送
                                yield f"data: {json.dumps({'content': cleaned_data})}\n\n"
                                # 给前端一些时间处理
                                await asyncio.sleep(0.01)
                    except UnicodeDecodeError:
                        continue

            # 处理剩余的 buffer
            if buffer:
                try:
                    line = buffer.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:].strip('"')
                        if data and data != '\\n':
                            cleaned_data = data.replace('\\n', '\n')
                            yield f"data: {json.dumps({'content': cleaned_data})}\n\n"
                except UnicodeDecodeError:
                    pass

            # After streaming is done, send retrieval metadata if available
            if retrieval_results:
                yield f"data: {json.dumps({'type': 'metadata', 'retrieval_results': retrieval_results, 'retrieval_source': 'rag'})}\n\n"
        else:
            # 非流式响应
            yield f"data: {json.dumps({'content': 'Non-streaming response received'})}\n\n"

        # 发送完成信号
        yield f"data: {json.dumps({'done': True})}\n\n"

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        yield f"data: {json.dumps({'error': error_msg})}\n\n"


@app.post("/chat")
async def chat(request: Request):
    """聊天接口 - 支持流式响应、附件上传、用户身份验证和会话管理"""
    try:
        body = await request.json()
        prompt = body.get("message", "")
        attachments = body.get("attachments", [])
        user_id = body.get("user_id")  # 提取用户 ID
        session_id = body.get("session_id")  # 提取 session ID

        if not prompt and not attachments:
            return {"error": "Message or attachments required"}

        return StreamingResponse(
            stream_agent_response(prompt, attachments, user_id, session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
            }
        )

    except Exception as e:
        return {"error": str(e)}


# ==================== 反馈系统 API ====================

@app.post("/api/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    """
    提交用户反馈

    用户对 Agent 回答进行点赞/点踩
    """
    if not FEEDBACK_ENABLED:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": "Feedback system is not available"
            }
        )

    try:
        result = await submit_feedback(request)
        return result
    except Exception as e:
        print(f"Feedback error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )


@app.get("/api/feedback/health")
async def feedback_health_endpoint():
    """反馈系统健康检查"""
    if not FEEDBACK_ENABLED:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "message": "Feedback system is not enabled"
            }
        )

    try:
        result = await health_check()
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )


@app.get("/api/feedback/stats")
async def feedback_stats_endpoint():
    """获取反馈统计"""
    if not FEEDBACK_ENABLED:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "message": "Feedback system is not enabled"
            }
        )

    try:
        result = await get_feedback_stats()
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )


if __name__ == "__main__":
    import uvicorn

    # 获取端口（默认 8080）
    port = int(os.environ.get("PORT", 8080))

    print(f"🚀 Starting AWS Support Agent Web Client on port {port}")
    print(f"📍 Region: {REGION}")

    try:
        agent_arn = get_agent_arn()
        print(f"✅ Agent ARN: {agent_arn}")
    except Exception as e:
        print(f"⚠️  Agent ARN not configured: {e}")

    # Knowledge Base 配置已在文件开头通过环境变量设置（第 20-21 行）
    # 不需要在这里再调用 configure_kb()
    if FEEDBACK_ENABLED:
        from feedback.config import get_config_summary
        config = get_config_summary()
        if config['thumbs_up_rag_update'] == 'ENABLED':
            print(f"✅ Knowledge Base configured: KB={config['knowledge_base_id']}, Bucket={config['kb_s3_bucket']}")
        else:
            print(f"⚠️  Knowledge Base not configured (thumbs_up RAG update disabled)")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
