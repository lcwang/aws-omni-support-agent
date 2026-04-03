# 点赞更新 RAG 功能配置指南

> 详细说明如何开启和配置点赞自动更新 Knowledge Base 功能

**更新时间**: 2026-04-03
**状态**: ✅ 可选功能

---

## 📋 功能说明

### 点赞更新 RAG 是什么？

当用户对 Agent 的回答点赞 👍 时，系统会：

1. **判断答案来源**
   - RAG 召回：提升相关文档的权重
   - LLM 生成：将新知识加入 RAG
   - 混合模式：提取精华加入 RAG

2. **自动更新 Knowledge Base**
   - 新建 Markdown 格式的 QA 文档
   - 上传到 S3 数据源
   - 触发 Bedrock KB 同步（ingestion job）
   - Knowledge Base 自动 embedding 并索引

3. **生效**
   - 未来相同或类似的问题可以检索到这个验证过的 QA
   - 提升答案质量和一致性

---

## 🔧 实现原理

### 数据流

```
用户点赞 👍
  ↓
positive_handler.py
  ├─ 场景A: RAG召回 → boost_document_priority()
  ├─ 场景B: LLM生成 → add_validated_qa_to_kb()
  └─ 场景C: 混合模式 → 判断后决定
      ↓
bedrock_kb_operations.py: add_validated_qa_to_kb()
      ↓
1. 生成 Markdown 文档
   # {问题}

   {答案}

   ---
   Validated at: {时间}
   Source: User Feedback

2. 上传到 S3
   s3_client.put_object(
       Bucket=S3_BUCKET,
       Key="validated-qa/{doc_id}.txt",
       Body=content
   )

3. 触发 Knowledge Base 同步
   bedrock_agent_client.start_ingestion_job(
       knowledgeBaseId=KNOWLEDGE_BASE_ID,
       dataSourceId=data_source_id
   )
      ↓
Bedrock Knowledge Base 自动处理:
- 检测 S3 新文件
- 使用 Titan Embeddings 生成向量
- 更新 OpenSearch 索引
      ↓
新 QA 可以被检索
```

---

## 🚀 如何开启

### 前提条件

1. **已创建 Bedrock Knowledge Base**
   - 数据源类型：S3
   - 向量数据库：OpenSearch Serverless

2. **S3 Bucket 已配置**
   - 作为 Knowledge Base 的数据源
   - 已设置正确的 IAM 权限

---

### 方法 1: 使用 .env 文件（推荐）

编辑 `06_web_client_with_feedback/.env` 文件（如果不存在，从 `.env.example` 复制）：

```bash
cd 06_web_client_with_feedback
cp .env.example .env
vim .env  # 或用你喜欢的编辑器
```

添加以下配置：

```bash
# Knowledge Base 配置（可选，用于点赞更新 RAG）
KNOWLEDGE_BASE_ID=YOUR_KB_ID
KB_S3_BUCKET=your-s3-bucket-name
KB_S3_PREFIX=validated-qa/
```

**替换为你的实际值**：
- `YOUR_KB_ID` → 你的 Knowledge Base ID（例如：OWYUVBRMPH）
- `your-s3-bucket-name` → 你的 S3 bucket **名称**（不是 ARN）

然后启动服务：
```bash
./start.sh
```

`start.sh` 脚本会自动加载 `.env` 文件，`feedback/config.py` 会读取环境变量。**无需修改任何代码**。

---

### 方法 2: 直接导出环境变量（临时）

如果不想创建 `.env` 文件，可以在启动前导出环境变量：

```bash
export KNOWLEDGE_BASE_ID="YOUR_KB_ID"
export KB_S3_BUCKET="your-s3-bucket-name"
export KB_S3_PREFIX="validated-qa/"  # 可选，默认就是这个

python3 app.py
```

这种方式适合临时测试，但不推荐在生产环境使用（环境变量会在 shell session 结束后丢失）。

---

## 📝 配置参数说明

### knowledge_base_id

**是什么**: Bedrock Knowledge Base 的唯一标识符

**格式**: 10-12 位字母大写字符串，例如：`YOUR_KB_ID`

**如何获取**:

```bash
# 方法1: AWS CLI
aws bedrock-agent list-knowledge-bases \
  --region us-east-1 \
  --query 'knowledgeBaseSummaries[*].[name,knowledgeBaseId]' \
  --output table

# 方法2: AWS Console
# 1. 打开 Amazon Bedrock Console
# 2. 左侧菜单 → Knowledge bases
# 3. 点击你的 Knowledge Base
# 4. 在详情页面找到 "Knowledge base ID"
```

**示例输出**:
```
--------------------------------
|  ListKnowledgeBases          |
+------------------------+-----+
|  my-support-kb         | YOUR_KB_ID |
+------------------------+-----+
```

---

### s3_bucket

**是什么**: S3 bucket 的**名称**（name），不是 ARN

**格式**:
- ✅ 正确: `"my-kb-data-source"`
- ✅ 正确: `"support-agent-kb-us-east-1"`
- ❌ 错误: `"arn:aws:s3:::my-kb-data-source"`
- ❌ 错误: `"s3://my-kb-data-source"`

**如何获取**:

```bash
# 方法1: 从 Knowledge Base 配置中获取
aws bedrock-agent list-data-sources \
  --knowledge-base-id YOUR_KB_ID \
  --region us-east-1 \
  --query 'dataSourceSummaries[*].[name,dataSourceId]'

# 然后获取数据源详情
aws bedrock-agent get-data-source \
  --knowledge-base-id YOUR_KB_ID \
  --data-source-id YOUR_DATA_SOURCE_ID \
  --region us-east-1 \
  --query 'dataSource.dataSourceConfiguration.s3Configuration.bucketArn'

# 从 ARN 中提取 bucket name
# arn:aws:s3:::my-kb-data-source → my-kb-data-source

# 方法2: AWS Console
# 1. 打开 Knowledge Base
# 2. Data source 标签页
# 3. 查看 S3 URI: s3://bucket-name/prefix/
```

**注意**: 必须使用 Knowledge Base 已经配置的 S3 bucket，否则同步不会生效。

---

## ✅ 验证配置

### 1. 启动时检查日志

```bash
python3 app.py
```

**成功**:
```
✅ Feedback system enabled
✅ Knowledge Base configured for feedback RAG updates
Configuration: {'knowledge_base_id': 'YOUR_KB_ID', 's3_bucket': 'my-kb-data-source', 'thumbs_up_rag_update': 'ENABLED'}
```

**失败**:
```
⚠️ Knowledge Base not configured: ...
Configuration: {'thumbs_up_rag_update': 'DISABLED'}
```

### 2. 测试点赞功能

1. 启动服务并发送问题
2. 点击 👍
3. 查看服务器日志

**期望日志**:
```
[Positive] Processing thumbs_up for message msg_...
[Positive] LLM thumbs_up: adding validated QA to RAG
[Bedrock KB] Adding validated QA: 如何配置 S3 跨区域复制？...
[Bedrock KB] Uploaded to S3: s3://my-kb-data-source/validated-qa/abc123.txt
[Bedrock KB] Sync triggered: ingestion-job-xyz
```

### 3. 验证 S3 文件

```bash
# 列出 validated-qa 目录
aws s3 ls s3://my-kb-data-source/validated-qa/

# 查看文件内容
aws s3 cp s3://my-kb-data-source/validated-qa/abc123.txt -
```

**期望内容**:
```markdown
# 如何配置 S3 跨区域复制？

要配置 S3 跨区域复制，需要以下步骤：
1. 在源 bucket 启用版本控制
2. 创建 IAM 角色授予复制权限
3. ...

---
Validated at: 2026-04-03T10:30:00Z
Source: User Feedback
```

### 4. 验证 Ingestion Job

```bash
# 列出最近的 ingestion jobs
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id YOUR_KB_ID \
  --data-source-id YOUR_DATA_SOURCE_ID \
  --region us-east-1 \
  --max-results 5

# 查看 job 状态
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id YOUR_KB_ID \
  --data-source-id YOUR_DATA_SOURCE_ID \
  --ingestion-job-id JOB_ID \
  --region us-east-1 \
  --query 'ingestionJob.status'
```

**状态**:
- `IN_PROGRESS` - 正在同步
- `COMPLETE` - 同步完成 ✅
- `FAILED` - 失败 ❌

---

## 🔍 常见问题

### Q1: s3_bucket 是 bucket name 还是 ARN？

**答案**: **Bucket Name**（名称）

```python
# ✅ 正确
s3_bucket="my-kb-data-source"

# ❌ 错误
s3_bucket="arn:aws:s3:::my-kb-data-source"
```

代码中使用的是 `boto3` 的 `s3_client.put_object(Bucket=...)`，这个参数必须是 bucket name。

---

### Q2: 点赞后多久可以检索到新内容？

**答案**: 取决于 Ingestion Job 的执行时间

- 触发同步：立即（几秒内）
- Ingestion Job 执行：3-10 分钟（取决于文件大小和数量）
- 索引更新：Ingestion Job 完成后立即生效

**优化建议**:
- 小文件（< 1KB）：通常 3-5 分钟
- 批量同步：建议定时批量（例如每小时一次）而不是每次点赞都触发

---

### Q3: 能否自定义 S3 文件路径？

**答案**: 可以，通过 `KB_S3_PREFIX` 环境变量

```python
# 默认: validated-qa/
KB_S3_PREFIX = "validated-qa/"

# 自定义
export KB_S3_PREFIX="user-feedback/validated/"
```

文件会保存到: `s3://bucket/user-feedback/validated/{doc_id}.txt`

**注意**: 确保 Knowledge Base 的数据源配置包含这个 prefix。

---

### Q4: 如何避免每次点赞都触发同步？

**答案**: 使用环境变量禁用自动同步，改用定时批量同步

**方法 1: 通过环境变量禁用自动同步（推荐）**

在 `.env` 文件中添加：

```bash
AUTO_TRIGGER_INGESTION=false
```

或者直接不设置 `KNOWLEDGE_BASE_ID`，这样点赞后只会上传到 S3，不会触发同步。

**方法 2: 使用 Lambda 定时同步**

创建一个 Lambda 函数，使用 EventBridge 定时触发（例如每小时一次）:

```python
import boto3

def lambda_handler(event, context):
    bedrock = boto3.client('bedrock-agent', region_name='us-east-1')

    response = bedrock.start_ingestion_job(
        knowledgeBaseId='YOUR_KB_ID',
        dataSourceId='YOUR_DATA_SOURCE_ID'
    )

    return {
        'statusCode': 200,
        'body': f"Ingestion job started: {response['ingestionJob']['ingestionJobId']}"
    }
```

**EventBridge 规则**:
```
rate(1 hour)  # 每小时同步一次
```

---

### Q5: 点赞权重提升（boost_document_priority）是如何实现的？

**答案**: 目前是**记录版本**，不直接修改 OpenSearch

```python
async def boost_document_priority(documents, boost_amount):
    """
    提升文档权重（Bedrock KB 版本）

    注意：Bedrock Knowledge Base 不支持直接更新文档权重
    替代方案：记录到 DynamoDB，定期分析高质量文档
    """
    doc_ids = [doc.doc_id for doc in documents]

    # 记录到 DynamoDB（用于后续分析）
    # TODO: 实现 DynamoDB 记录逻辑

    return doc_ids
```

**完整实现需要**:
1. 创建 `high-quality-documents` DynamoDB 表
2. 记录点赞的文档 ID 和次数
3. 定期分析并调整检索策略（例如修改 retrieval configuration）

---

## 🎯 推荐配置

### 开发环境

在 `.env` 文件中配置（快速验证，每次点赞都同步）：

```bash
# .env
KNOWLEDGE_BASE_ID=YOUR_KB_ID
KB_S3_BUCKET=my-kb-dev
KB_S3_PREFIX=validated-qa/
```

### 生产环境

**选项 1: 只上传 S3，不自动同步（推荐）**

```bash
# .env
KNOWLEDGE_BASE_ID=YOUR_KB_ID
KB_S3_BUCKET=my-kb-prod
KB_S3_PREFIX=validated-qa/
AUTO_TRIGGER_INGESTION=false  # 禁用自动同步
```

然后使用 Lambda + EventBridge 每小时批量同步一次。

**选项 2: 完全手动同步**

不在 `.env` 中设置 `KNOWLEDGE_BASE_ID`，这样系统只会记录点赞，不会上传到 S3。需要时手动运行同步脚本。

**优势**:
- 减少 API 调用次数
- 降低成本
- 避免频繁触发 ingestion job

---

## 📊 成本考虑

### API 调用

每次点赞（LLM 生成场景）:
- 1x S3 PutObject: $0.005 per 1,000 requests
- 1x Bedrock Agent StartIngestionJob: 包含在 KB 费用中

### Ingestion Job

- 按处理的文档大小计费
- 单个 QA 文档 ~1KB
- 成本极低（< $0.01 per 1,000 documents）

### 优化建议

- 使用批量同步（每小时）而不是实时同步
- 小文件 (<1KB) 成本几乎可忽略
- 主要成本在 OpenSearch Serverless 存储

---

## 📚 相关文档

- [feedback/handlers/positive_handler.py](./feedback/handlers/positive_handler.py) - 点赞处理逻辑
- [feedback/operations/bedrock_kb_operations.py](./feedback/operations/bedrock_kb_operations.py) - Bedrock KB 操作
- [feedback/config.py](./feedback/config.py) - 配置管理
- [AWS Bedrock Knowledge Base 文档](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)

---

**版本**: 1.0
**最后更新**: 2026-04-03
**维护者**: AWS Omni Support Agent Team
