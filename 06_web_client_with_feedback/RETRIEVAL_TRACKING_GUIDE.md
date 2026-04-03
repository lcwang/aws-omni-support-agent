# 检索结果追踪功能说明

> 完整实现点赞/点踩反馈系统的检索追踪功能

**更新时间**: 2026-04-03
**状态**: ✅ 已完整实现

---

## 📋 功能说明

### 问题

之前的反馈系统虽然可以提交点赞/点踩，但缺少关键信息：**不知道答案是基于哪些文档生成的**。

这导致：
- ❌ 点赞时无法提升具体文档的权重
- ❌ 点踩时无法标记有问题的文档
- ❌ `rag_documents` 字段永远是空的 `[]`

### 解决方案

完整的数据流：

```
Agent (retrieve tool)
  ↓ 捕获检索结果
  ↓ 返回 metadata 事件
Web Client (app.py)
  ↓ 解析 metadata
  ↓ 传递给前端
前端 (script.js)
  ↓ 存储到消息 data 属性
  ↓ 用户点击 👍/👎
反馈系统 (feedback-ui.js)
  ↓ 读取 rag_documents
  ↓ 提交到后端
DynamoDB / Bedrock KB
```

---

## 🔧 实现细节

### 1. Agent 改动 (04_create_knowledge_mcp_gateway_Agent/aws_support_agent.py)

#### 1.1 包装 retrieve 工具

```python
# 导入原始 retrieve 工具
from strands_tools import agent_graph, retrieve as original_retrieve

# 全局变量存储检索结果
_last_retrieval_results = []

# 包装 retrieve 工具
@tool
def retrieve(query: str, number_of_results: int = 5) -> str:
    """捕获检索结果的包装工具"""
    global _last_retrieval_results

    # 调用原始工具
    result = original_retrieve(query=query, number_of_results=number_of_results)

    # 调用 Bedrock KB API 获取结构化结果
    kb_id = get_knowledge_base_id()
    bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)

    kb_response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={'text': query},
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': number_of_results
            }
        }
    )

    # 提取文档信息
    _last_retrieval_results = []
    for idx, item in enumerate(kb_response.get('retrievalResults', [])):
        doc_info = {
            "doc_id": f"doc_{idx}",
            "title": item.get('location', {}).get('s3Location', {}).get('uri', 'Unknown')[-50:],
            "chunk": item['content']['text'][:200],
            "score": item['score'],
            "source_url": item.get('location', {}).get('s3Location', {}).get('uri', None)
        }
        _last_retrieval_results.append(doc_info)

    return result
```

#### 1.2 返回 metadata 事件

```python
@app.entrypoint
async def strands_agent_bedrock(payload: Dict[str, Any]):
    global _last_retrieval_results
    _last_retrieval_results = []  # 清空之前的结果

    # 流式返回文本
    async for event in agent.stream_async(user_input_with_context):
        if "data" in event:
            yield event["data"]

    # 返回 metadata 事件
    if _last_retrieval_results:
        metadata_event = {
            "type": "metadata",
            "retrieval_results": _last_retrieval_results,
            "retrieval_source": "rag"
        }
        yield metadata_event
```

---

### 2. Web Client 改动 (06_web_client_with_feedback/app.py)

#### 2.1 解析 metadata 事件

```python
async def stream_agent_response(prompt, attachments, user_id, session_id):
    retrieval_results = []  # 存储检索结果

    # 处理流式响应
    while True:
        chunk = await loop.run_in_executor(None, stream.read, 1024)
        if not chunk:
            break

        buffer += chunk

        while b'\n' in buffer:
            line_bytes, buffer = buffer.split(b'\n', 1)
            line = line_bytes.decode('utf-8')

            if line.startswith('data: '):
                data_str = line[6:].strip()

                # 尝试解析为 JSON（可能是 metadata 事件）
                try:
                    data_obj = json.loads(data_str.strip('"'))

                    # 识别 metadata 事件
                    if isinstance(data_obj, dict) and data_obj.get('type') == 'metadata':
                        retrieval_results = data_obj.get('retrieval_results', [])
                        logger.info(f"Captured {len(retrieval_results)} retrieval results")
                        continue  # 不发送 metadata 作为内容

                except json.JSONDecodeError:
                    pass  # 不是 JSON，按文本处理

                # 普通文本内容
                if data_str and data_str != '\\n':
                    cleaned_data = data_str.strip('"').replace('\\n', '\n')
                    yield f"data: {json.dumps({'content': cleaned_data})}\n\n"

    # 在流式响应结束后，发送 metadata
    if retrieval_results:
        yield f"data: {json.dumps({'type': 'metadata', 'retrieval_results': retrieval_results, 'retrieval_source': 'rag'})}\n\n"
```

---

### 3. 前端改动 (06_web_client_with_feedback/static/script.js)

#### 3.1 接收 metadata 事件

```javascript
async function streamResponse(message, attachments) {
    let fullContent = '';
    let retrievalResults = [];  // 存储检索结果

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));

                // 识别 metadata 事件
                if (data.type === 'metadata') {
                    retrievalResults = data.retrieval_results || [];
                    console.log(`Captured ${retrievalResults.length} retrieval results for feedback`);
                }
                else if (data.content) {
                    fullContent += data.content;
                    assistantTextDiv.innerHTML = marked.parse(fullContent);
                }
            }
        }
    }

    // 更新消息 data 属性
    if (retrievalResults.length > 0) {
        const messageContainer = assistantTextDiv.parentElement.parentElement;
        messageContainer.setAttribute('data-retrieval-source', 'rag');
        messageContainer.setAttribute('data-rag-documents', JSON.stringify(retrievalResults));
        console.log(`Updated message with ${retrievalResults.length} retrieval results`);
    }
}
```

---

### 4. 反馈系统 (已有功能，无需改动)

反馈系统 `feedback-ui.js` 已经配置好读取 `rag_documents`：

```javascript
function getMessageData(messageElement) {
    return {
        question: messageElement.dataset.question,
        answer: messageElement.dataset.answer,
        interaction_type: messageElement.dataset.interactionType || 'qa',
        retrieval_source: messageElement.dataset.retrievalSource || 'unknown',
        rag_documents: JSON.parse(messageElement.dataset.ragDocuments || '[]')  // ✅ 读取检索结果
    };
}
```

---

## 📊 数据格式

### retrieval_results 格式

```json
[
    {
        "doc_id": "doc_0",
        "title": "s3://bucket/path/to/document.txt",
        "chunk": "This is the first 200 characters of the retrieved content...",
        "score": 0.95,
        "source_url": "s3://bucket/path/to/document.txt"
    },
    {
        "doc_id": "doc_1",
        "title": "s3://bucket/path/to/another.pdf",
        "chunk": "Another relevant chunk of text...",
        "score": 0.87,
        "source_url": "s3://bucket/path/to/another.pdf"
    }
]
```

### FeedbackRequest (提交到反馈 API)

```python
{
    "message_id": "msg_1234567890_abc123",
    "feedback_type": "thumbs_up",  # 或 "thumbs_down"
    "timestamp": "2026-04-03T10:30:00Z",

    "question": "如何配置 S3 跨区域复制？",
    "answer": "配置 S3 跨区域复制需要...",
    "interaction_type": "qa",

    "retrieval_source": "rag",
    "rag_documents": [  # ✅ 现在有值了！
        {
            "doc_id": "doc_0",
            "title": "s3://...",
            "chunk": "...",
            "score": 0.95,
            "source_url": "s3://..."
        }
    ],

    "user_id": "user@example.com",
    "session_id": "session_abc123"
}
```

---

## ✅ 验证步骤

### 1. 启动服务

```bash
cd 06_web_client_with_feedback
python3 app.py
```

### 2. 发送测试问题

访问 http://localhost:8000，发送一个问题，例如：
```
如何配置 S3 跨区域复制？
```

### 3. 检查浏览器控制台

应该看到：
```
Captured 5 retrieval results for feedback
Updated message with 5 retrieval results
```

### 4. 检查消息元素

在浏览器控制台运行：
```javascript
document.querySelector('.message.assistant').dataset.ragDocuments
```

应该返回 JSON 字符串，而不是 `[]`。

### 5. 点击 👍 或 👎

查看反馈请求的 payload：
```javascript
// 在 feedback-ui.js 的 submitFeedback() 中添加：
console.log('Feedback payload:', JSON.stringify(feedbackData, null, 2));
```

应该看到 `rag_documents` 数组有内容。

### 6. 检查 DynamoDB

```bash
aws dynamodb scan \
  --table-name support-agent-feedback-negative \
  --limit 1 \
  --query 'Items[0].retrieval_details'
```

应该包含 `rag_documents` 信息。

---

## 🎯 功能效果

### 点赞 (👍)

现在可以：
- ✅ 知道是哪些文档生成了好的答案
- ✅ 提升这些文档的权重 (`boost_document_priority`)
- ✅ 分析高质量文档的特征

### 点踩 (👎)

现在可以：
- ✅ 知道是哪些文档导致了错误答案
- ✅ 标记有问题的文档 (`flag_problematic_document`)
- ✅ 自动分类问题类型（`weak_retrieval` vs `bad_document`）

---

## 🔍 调试技巧

### Agent 日志

```bash
# 查看 Agent 是否捕获了检索结果
tail -f /path/to/agent/logs | grep "Captured.*retrieval results"
```

### Web Client 日志

```bash
# 查看 Web Client 是否解析了 metadata
tail -f /path/to/app/logs | grep "retrieval results"
```

### 浏览器控制台

```javascript
// 检查所有 assistant 消息的 rag_documents
document.querySelectorAll('.message.assistant').forEach(msg => {
    console.log(msg.dataset.messageId, JSON.parse(msg.dataset.ragDocuments).length);
});
```

---

## ⚠️ 注意事项

### 1. 性能影响

- 每次 retrieve 调用会额外调用一次 Bedrock KB API
- 影响：增加 ~50-100ms 延迟
- 优化：可以考虑解析 `original_retrieve` 的返回文本，而不是额外调用 API

### 2. Token 消耗

- 原始 retrieve：返回格式化文本
- 额外 KB API 调用：返回结构化数据
- 建议：监控 Bedrock KB API 调用次数

### 3. S3 URI 显示

- 目前 `title` 显示 S3 URI 的最后 50 个字符
- 可以改进：提取文件名，或者使用 S3 对象的 metadata

---

## 📚 相关文档

- [README.md](./README.md) - 整体架构
- [COMPARISON.md](./COMPARISON.md) - 与 05+06 方案对比
- [feedback/operations/bedrock_kb_operations.py](./feedback/operations/bedrock_kb_operations.py) - Bedrock KB 操作
- [feedback/handlers/positive_handler.py](./feedback/handlers/positive_handler.py) - 点赞处理逻辑
- [feedback/handlers/negative_handler.py](./feedback/handlers/negative_handler.py) - 点踩处理逻辑

---

**版本**: 1.0
**最后更新**: 2026-04-03
**维护者**: AWS Omni Support Agent Team
