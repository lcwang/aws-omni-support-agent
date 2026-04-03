# 环境变量配置指南

> 安全地配置 Knowledge Base 和其他敏感信息

**更新时间**: 2026-04-03

---

## 🎯 为什么使用环境变量？

❌ **不安全**（硬编码在代码中）:
```python
knowledge_base_id = "YOUR_KB_ID"  # 敏感信息暴露在代码中
s3_bucket = "my-bucket"           # 可能被提交到 Git
```

✅ **安全**（使用环境变量）:
```python
knowledge_base_id = os.environ.get('KNOWLEDGE_BASE_ID')  # 从环境读取
s3_bucket = os.environ.get('KB_S3_BUCKET')               # 不会提交到 Git
```

**优点**:
- 配置与代码分离
- 不会意外提交到版本控制
- 不同环境可以使用不同配置
- 遵循 [12-Factor App](https://12factor.net/config) 最佳实践

---

## 📋 配置方式

### 方式 1: 使用 .env 文件（推荐）

#### 步骤 1: 创建 .env 文件

```bash
cd 06_web_client_with_feedback
cp .env.example .env
```

#### 步骤 2: 编辑 .env 文件

```bash
nano .env
# 或
vim .env
# 或
code .env  # VS Code
```

填入你的配置：

```bash
# AWS 配置
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Agent 配置
AGENT_ARN=arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/your-agent-id

# Knowledge Base 配置（可选，用于点赞更新 RAG）
KNOWLEDGE_BASE_ID=YOUR_KB_ID
KB_S3_BUCKET=your-s3-bucket-name
KB_S3_PREFIX=validated-qa/

# DynamoDB 配置
FEEDBACK_TABLE_NAME=support-agent-feedback-negative

# 其他配置
PORT=8000
TEST_MODE=0
```

#### 步骤 3: 启动服务

```bash
./start.sh
```

`start.sh` 脚本会自动加载 `.env` 文件中的配置。

---

### 方式 2: 命令行参数

```bash
./start.sh \
  --kb-id YOUR_KB_ID \
  --bucket your-s3-bucket-name \
  --port 8000
```

---

### 方式 3: Shell 环境变量（临时）

```bash
export KNOWLEDGE_BASE_ID="YOUR_KB_ID"
export KB_S3_BUCKET="your-s3-bucket-name"
export PORT=8000

python3 app.py
```

---

### 方式 4: Shell 配置文件（永久）

添加到 `~/.zshrc` 或 `~/.bashrc`:

```bash
# AWS Support Agent 配置
export KNOWLEDGE_BASE_ID="YOUR_KB_ID"
export KB_S3_BUCKET="your-s3-bucket-name"
```

重新加载配置：

```bash
source ~/.zshrc  # 或 source ~/.bashrc
```

---

## 📝 必需 vs 可选配置

### 必需配置

这些配置**必须**设置，否则服务无法启动：

| 变量 | 说明 | 如何获取 |
|------|------|----------|
| `FEEDBACK_TABLE_NAME` | DynamoDB 表名 | 默认: `support-agent-feedback-negative` |

### 可选配置

这些配置**可选**，不设置也能运行，但某些功能会不可用：

| 变量 | 说明 | 影响功能 |
|------|------|----------|
| `KNOWLEDGE_BASE_ID` | Knowledge Base ID | 点赞更新 RAG |
| `KB_S3_BUCKET` | S3 Bucket 名称 | 点赞更新 RAG |
| `AGENT_ARN` | Agent Runtime ARN | 如果有 `launch_result.pkl` 可不设置 |
| `PORT` | 服务端口 | 默认: 8000 |

---

## 🔍 如何获取配置值

### 获取 Knowledge Base ID

```bash
aws bedrock-agent list-knowledge-bases \
  --region us-east-1 \
  --query 'knowledgeBaseSummaries[*].[name,knowledgeBaseId]' \
  --output table
```

### 获取 S3 Bucket 名称

```bash
# 方法 1: 从 Knowledge Base 查询
aws bedrock-agent list-data-sources \
  --knowledge-base-id YOUR_KB_ID \
  --region us-east-1

# 方法 2: AWS Console
# Bedrock → Knowledge bases → 你的 KB → Data sources 标签页
```

### 获取 Agent ARN

```bash
# 方法 1: 从 pickle 文件读取（自动）
python3 -c "
import pickle
with open('../launch_result.pkl', 'rb') as f:
    result = pickle.load(f)
print(result.agent_arn)
"

# 方法 2: AWS Console
# Bedrock → Agents → Agent runtimes
```

---

## ✅ 验证配置

启动服务后检查日志：

```bash
./start.sh
```

**成功**:
```
========================================
AWS Support Agent Web Client
========================================

✓ 找到 .env 文件，加载配置...

📋 配置检查:
  AWS Region: us-east-1
  Port: 8000
  Agent ARN: ✓ 已配置
  Knowledge Base: ✓ 已配置
    - KB ID: YOUR_KB_ID
    - S3 Bucket: your-s3-bucket-name
  DynamoDB 表: ✓ support-agent-feedback-negative

========================================
🚀 启动服务...
========================================

✅ Feedback system enabled
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**失败**（缺少配置）:
```
  Knowledge Base: ⚠ 未配置（点赞更新 RAG 功能不可用）
```

---

## 🔒 安全最佳实践

### 1. 不要提交 .env 到 Git

确保 `.gitignore` 包含：

```gitignore
.env
.env.local
.env.*.local
*.pkl
```

检查：
```bash
git status
# 确保 .env 显示在 "Untracked files" 中
```

### 2. 使用 .env.example 作为模板

- `.env.example` - 提交到 Git，包含变量名但不包含真实值
- `.env` - 不提交，包含真实配置

### 3. 不同环境使用不同配置

```bash
.env.dev        # 开发环境
.env.staging    # 测试环境
.env.prod       # 生产环境

# 加载指定环境
cp .env.prod .env
./start.sh
```

### 4. 限制文件权限

```bash
chmod 600 .env  # 仅当前用户可读写
```

### 5. 容器部署时使用 Secrets

**Docker**:
```bash
docker run -e KNOWLEDGE_BASE_ID=xxx -e KB_S3_BUCKET=yyy ...
```

**ECS**:
```json
{
  "secrets": [
    {
      "name": "KNOWLEDGE_BASE_ID",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:kb-id"
    }
  ]
}
```

**Kubernetes**:
```yaml
env:
  - name: KNOWLEDGE_BASE_ID
    valueFrom:
      secretKeyRef:
        name: app-secrets
        key: kb-id
```

---

## 🎯 完整示例

### 开发环境配置

```bash
# .env
AWS_REGION=us-east-1
KNOWLEDGE_BASE_ID=YOUR_KB_ID
KB_S3_BUCKET=my-kb-dev-bucket
PORT=8000
```

启动：
```bash
./start.sh
```

---

### 生产环境配置

```bash
# .env.prod
AWS_REGION=us-east-1
KNOWLEDGE_BASE_ID=PROD_KB_ID
KB_S3_BUCKET=my-kb-prod-bucket
PORT=80

# 从 AWS Secrets Manager 读取
# (需要额外实现)
```

---

### 测试 UI（不需要真实配置）

```bash
export TEST_MODE=1
python3 app.py
```

---

## 📚 相关文档

- [README.md](./README.md) - 项目总览
- [THUMBS_UP_RAG_SETUP.md](./THUMBS_UP_RAG_SETUP.md) - 点赞更新 RAG 配置
- [12-Factor App - Config](https://12factor.net/config) - 配置最佳实践

---

## ❓ 常见问题

### Q1: .env 文件不生效怎么办？

**检查**:
1. 文件名是否正确（`.env` 不是 `env.txt`）
2. 是否在正确的目录（`06_web_client_with_feedback/`）
3. 是否使用了 `./start.sh` 启动

### Q2: 可以在代码中硬编码配置吗？

**不推荐**！但如果是开发测试，可以这样：

```python
# 仅用于本地开发测试
if os.environ.get('ENV') == 'development':
    os.environ.setdefault('KNOWLEDGE_BASE_ID', 'test-kb-id')
```

### Q3: 如何在不同团队成员间共享配置？

**方案 1**: 使用密码管理工具（1Password, LastPass）
**方案 2**: 使用团队 Wiki 记录（加密存储）
**方案 3**: 使用 AWS Secrets Manager（推荐生产环境）

---

**版本**: 1.0
**最后更新**: 2026-04-03
**维护者**: AWS Omni Support Agent Team
