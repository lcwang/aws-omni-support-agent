# 🚀 部署指南 - 混合架构

> **架构策略**: 基础设施在 SageMaker Notebook（手动/偶尔），应用代码在 GitHub Actions（自动/频繁）

---

## 📊 架构概览

```
┌──────────────────────────────────────────────────────────┐
│                   代码托管 (GitHub)                       │
│  - Lambda 代码                                           │
│  - Agent 代码                                            │
│  - 基础设施 Notebooks                                    │
└──────────────────────────────────────────────────────────┘
              ↓                           ↓
    ┌──────────────────┐       ┌──────────────────┐
    │ GitHub Actions   │       │ SageMaker        │
    │ (自动)           │       │ Notebook (手动)  │
    │                  │       │                  │
    │ ✓ Lambda 部署    │       │ ✓ Knowledge Base │
    │ ✓ 代码测试       │       │ ✓ Gateway        │
    │ ✓ 安全扫描       │       │ ✓ Agent Runtime  │
    └──────────────────┘       └──────────────────┘
              ↓                           ↓
         ┌────────────────────────────────────────┐
         │          AWS 环境                      │
         │  DEV / STAGING / PROD                 │
         └────────────────────────────────────────┘
```

---

## 🎯 两种部署类型

### 类型 1️⃣: 基础设施部署（SageMaker Notebook）⚙️

**什么时候需要**:
- ✅ 首次搭建环境
- ✅ 创建新的 Knowledge Base
- ✅ 更新 Gateway 配置
- ✅ Agent Runtime 重大架构变更

**频率**: 偶尔（每月 < 5 次）

**工具**: SageMaker Jupyter Notebook

**位置**:
```
01_create_support_knowledegbase_rag/create_knowledge_base.ipynb
03_create_agentcore_gateway/create_agentcore_gateway.ipynb
04_create_knowledge_mcp_gateway_Agent/deploy_QA_agent.ipynb
```

---

### 类型 2️⃣: 应用代码部署（GitHub Actions）🤖

**什么时候需要**:
- ✅ Lambda 函数 bug 修复
- ✅ 新增/修改工具函数
- ✅ Agent System Prompt 优化
- ✅ 配置参数调整

**频率**: 频繁（每天可能多次）

**工具**: GitHub Actions（自动触发）

**位置**:
```
02_AWS_Support_Case_Lambda/lambda_handler.py
04_create_knowledge_mcp_gateway_Agent/aws_support_agent.py
```

---

## 📋 部署清单

### ✅ 初次部署完整清单

#### Phase 1: 基础设施（SageMaker Notebook）

##### 1.1 启动 SageMaker Notebook Instance
```bash
# 在 AWS Console 或使用 CLI
aws sagemaker create-notebook-instance \
  --notebook-instance-name support-agent-dev \
  --instance-type ml.t3.medium \
  --role-arn arn:aws:iam::YOUR_ACCOUNT:role/SageMakerExecutionRole
```

##### 1.2 克隆代码到 Notebook
```bash
# 在 SageMaker Notebook Terminal 中
cd SageMaker
git clone https://github.com/percy-han/aws-omni-support-agent.git
cd aws-omni-support-agent
```

##### 1.3 创建 Knowledge Base
```
📓 打开并执行:
01_create_support_knowledegbase_rag/create_knowledge_base.ipynb

⏱️ 预计时间: 15-20 分钟
📝 记录输出: Knowledge Base ID
```

**重要参数**:
- `kb_name`: aws-support-kb-dev
- `data_source`: S3 bucket with AWS docs
- `embedding_model`: amazon.titan-embed-text-v1

**输出示例**:
```python
knowledge_base_id = "KB123456789"
# 保存到 SSM Parameter Store
```

##### 1.4 创建 AgentCore Gateway
```
📓 打开并执行:
03_create_agentcore_gateway/create_agentcore_gateway.ipynb

⏱️ 预计时间: 10-15 分钟
📝 记录输出: Gateway URL
```

**重要参数**:
- `gateway_name`: aws-support-gateway-dev
- `region`: us-east-1

**输出示例**:
```python
gateway_url = "https://gateway-xxxxx.execute-api.us-east-1.amazonaws.com"
# 保存到 SSM Parameter Store
```

##### 1.5 首次部署 Agent Runtime
```
📓 打开并执行:
04_create_knowledge_mcp_gateway_Agent/deploy_QA_agent.ipynb

⏱️ 预计时间: 20-30 分钟
📝 记录输出: Agent ARN
```

**重要参数**:
- `agent_name`: AWS_Support_Agent_DEV
- `model_id`: claude-opus-4-5
- `memory_mode`: NO_MEMORY

**输出示例**:
```python
agent_arn = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/AWS_Support_Agent_DEV-xxxxx"
# 保存到 .bedrock_agentcore.yaml
```

---

#### Phase 2: Lambda 部署（GitHub Actions）

##### 2.1 配置 GitHub Secrets
```
进入仓库: Settings → Secrets and variables → Actions

添加 Secrets:
✓ AWS_ACCESS_KEY_ID_DEV
✓ AWS_SECRET_ACCESS_KEY_DEV
✓ AWS_ACCESS_KEY_ID_STAGING (可选)
✓ AWS_SECRET_ACCESS_KEY_STAGING (可选)
✓ AWS_ACCESS_KEY_ID_PROD
✓ AWS_SECRET_ACCESS_KEY_PROD
```

##### 2.2 配置 GitHub Environments
```
进入: Settings → Environments

创建环境:
✓ dev (无保护规则)
✓ staging (可选: 需要 1 人审批)
✓ prod (必需: 需要 1 人审批 + 5 分钟等待)
```

##### 2.3 首次 Lambda 部署
```bash
# 方式 1: 自动触发（推荐）
git add 02_AWS_Support_Case_Lambda/
git commit -m "feat: initial lambda deployment"
git push origin main
# GitHub Actions 自动部署到 DEV

# 方式 2: 手动触发
进入 GitHub: Actions → "Deploy Lambda to AWS" → Run workflow → 选择 dev
```

##### 2.4 验证部署
```bash
# 检查 Lambda 函数
aws lambda get-function \
  --function-name aws-support-tools-lambda-dev \
  --region us-east-1

# 测试调用
aws lambda invoke \
  --function-name aws-support-tools-lambda-dev \
  --payload '{"tool_name":"describe_severity_levels","parameters":{"language":"en"}}' \
  response.json

cat response.json
```

---

### ✅ 日常开发工作流

#### Scenario 1: 修复 Lambda Bug 🐛

```bash
# 1. 创建分支
git checkout -b fix/lambda-timeout

# 2. 修改代码
vim 02_AWS_Support_Case_Lambda/lambda_handler.py

# 3. 本地测试
cd 02_AWS_Support_Case_Lambda
python -c "import lambda_handler; print('✅ OK')"

# 4. 提交
git add .
git commit -m "fix: increase lambda timeout to 120s"
git push origin fix/lambda-timeout

# 5. 创建 PR（触发自动检查）
gh pr create --title "fix: increase lambda timeout to 120s"

# 6. PR 合并后自动部署到 DEV ✅

# 7. 手动部署到 PROD
# Actions → Deploy Lambda → Run workflow → Select "prod"
```

**时间**: 5-10 分钟
**自动化**: ✅ 完全自动

---

#### Scenario 2: 优化 Agent System Prompt 📝

```bash
# 1. 修改 Agent 代码
vim 04_create_knowledge_mcp_gateway_Agent/aws_support_agent.py

# 2. 本地验证
export INIT_MODE=lazy
python -c "import aws_support_agent; print(aws_support_agent.get_system_prompt()[:100])"

# 3. 提交
git add .
git commit -m "feat: improve agent prompt for e-commerce scenarios"
git push origin main

# 4. 在 SageMaker Notebook 中重新部署 Agent
打开: 04_create_knowledge_mcp_gateway_Agent/deploy_QA_agent.ipynb
执行: 更新 Agent 的部分（不需要重建 Docker）
```

**时间**: 15-20 分钟
**自动化**: ⚠️ 部分自动（代码提交自动，Agent 部署手动）

---

#### Scenario 3: 添加新的 Lambda 工具 🔧

```bash
# 1. 编辑 lambda_handler.py
vim 02_AWS_Support_Case_Lambda/lambda_handler.py

# 添加新工具
def describe_trusted_advisor(event: Dict[str, Any]) -> Dict[str, Any]:
    """查询 Trusted Advisor 检查结果"""
    # ... 实现

# 添加到路由表
TOOL_HANDLERS = {
    # ... 现有工具
    'describe_trusted_advisor': describe_trusted_advisor
}

# 2. 更新 Gateway 工具定义
vim 02_AWS_Support_Case_Lambda/gateway_tools_schema.json
# 添加新工具的 schema

# 3. 提交并部署
git add .
git commit -m "feat: add trusted advisor tool"
git push origin main

# 4. 在 AWS Console 更新 Gateway 配置
# Bedrock → AgentCore → Gateways → 你的 Gateway
# 添加新工具映射: describe_trusted_advisor
```

**时间**: 30-45 分钟
**自动化**: ⚠️ Lambda 自动，Gateway 配置手动

---

#### Scenario 4: 更新 Knowledge Base 内容 📚

```bash
# 1. 在 SageMaker Notebook 中
打开: 01_create_support_knowledegbase_rag/create_knowledge_base.ipynb

# 2. 上传新文档到 S3
aws s3 cp new_docs/ s3://your-kb-bucket/docs/ --recursive

# 3. 执行 Notebook 的数据源同步部分
# 运行指定的 cells 触发重新索引

# 4. 验证
# 测试检索新内容
```

**时间**: 20-30 分钟
**自动化**: ❌ 完全手动

---

### ✅ 环境管理

#### DEV 环境
```
用途: 开发和测试
自动部署: ✅ 是（Lambda）
审批需求: ❌ 无
数据: 测试数据
```

**Lambda 命名**: `aws-support-tools-lambda-dev`
**Agent 命名**: `AWS_Support_Agent_DEV`
**SSM 参数前缀**: `/support/dev/`

---

#### STAGING 环境（可选）
```
用途: 预生产验证
自动部署: ⚠️ 手动触发
审批需求: ⚠️ 可选
数据: 生产副本
```

**Lambda 命名**: `aws-support-tools-lambda-staging`
**Agent 命名**: `AWS_Support_Agent_STAGING`
**SSM 参数前缀**: `/support/staging/`

---

#### PROD 环境
```
用途: 生产环境
自动部署: ❌ 手动触发 + 审批
审批需求: ✅ 必需（至少 1 人）
数据: 真实生产数据
```

**Lambda 命名**: `aws-support-tools-lambda-prod`
**Agent 命名**: `AWS_Support_Agent_PROD`
**SSM 参数前缀**: `/support/prod/`

---

## 🔄 回滚操作

### Lambda 回滚
```bash
# 查看版本
aws lambda list-versions-by-function \
  --function-name aws-support-tools-lambda-prod

# 回滚到上一版本
aws lambda update-alias \
  --function-name aws-support-tools-lambda-prod \
  --name PROD \
  --function-version <previous-version>
```

### Agent Runtime 回滚
```
在 SageMaker Notebook 中:
1. 回退到之前的代码版本: git checkout <commit-hash>
2. 重新执行 deploy_QA_agent.ipynb
3. 或者恢复之前的 Docker 镜像
```

---

## 📊 监控和验证

### Lambda 监控
```bash
# CloudWatch Logs
aws logs tail /aws/lambda/aws-support-tools-lambda-prod --follow

# Metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=aws-support-tools-lambda-prod \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### Agent Runtime 监控
```bash
# 使用 agent_client.py 测试
cd 04_create_knowledge_mcp_gateway_Agent
python agent_client.py

# 或者通过 AWS Console
# Bedrock → AgentCore → Runtimes → 你的 Agent → Test
```

---

## 🆘 故障排除

### 问题 1: GitHub Actions 部署失败

**错误**: `AWS credentials not configured`

**解决**:
```bash
# 检查 GitHub Secrets 是否配置
# Settings → Secrets → AWS_ACCESS_KEY_ID_DEV 存在？

# 测试凭证
aws sts get-caller-identity
```

---

### 问题 2: SageMaker Notebook 执行失败

**错误**: `ModuleNotFoundError: No module named 'bedrock_agentcore'`

**解决**:
```bash
# 在 Notebook Terminal 中
pip install -r 04_create_knowledge_mcp_gateway_Agent/requirements.txt
```

---

### 问题 3: Lambda 调用超时

**错误**: `Task timed out after 60.00 seconds`

**解决**:
```python
# 在 deploy_lambda.py 中修改
LAMBDA_TIMEOUT = 120  # 增加到 120 秒

# 重新部署
python deploy_lambda.py
```

---

## 📚 相关文档

- 📄 [CI/CD 架构对比](.github/CICD_COMPARISON.md)
- 📄 [Notebook CI/CD 策略](aws-cicd/NOTEBOOK_CICD_STRATEGY.md)
- 📄 [GitHub Actions 配置指南](.github/CICD_SETUP.md)
- 📄 [快速参考](.github/QUICK_REFERENCE.md)

---

## ✅ 检查清单

### 首次部署前
- [ ] SageMaker Notebook Instance 已创建
- [ ] GitHub Secrets 已配置
- [ ] GitHub Environments 已创建
- [ ] AWS CLI 已配置
- [ ] IAM 权限已验证

### 基础设施部署后
- [ ] Knowledge Base ID 已保存到 SSM
- [ ] Gateway URL 已保存到 SSM
- [ ] Agent ARN 已记录
- [ ] .bedrock_agentcore.yaml 已更新

### Lambda 部署后
- [ ] Lambda 函数可调用
- [ ] 所有 7 个工具测试通过
- [ ] CloudWatch Logs 正常
- [ ] IAM 权限正确

### 生产发布前
- [ ] DEV 环境测试通过
- [ ] STAGING 测试通过（如有）
- [ ] PR 已审批
- [ ] 监控告警已配置
- [ ] 回滚方案已准备

---

## 🎯 总结

### 你的工作流现在是

**频繁更新** (每天)：
```
修改 Lambda 代码 → git push → GitHub Actions 自动部署 ✅
```

**偶尔更新** (每月)：
```
打开 SageMaker Notebook → 执行相应 .ipynb → 验证资源 ✅
```

**最佳实践**:
- ✅ 小步快跑：每次只改一个功能
- ✅ 先测后部署：DEV → STAGING → PROD
- ✅ 保持简单：不要过度自动化基础设施
- ✅ 文档更新：重大变更同步更新文档

---

**祝部署顺利！** 🚀

有问题随时查看文档或创建 Issue。
