# CI/CD 配置指南

本文档说明如何配置和使用项目的 CI/CD 流程。

## 📋 目录

- [架构概览](#架构概览)
- [前置要求](#前置要求)
- [GitHub 配置](#github-配置)
- [AWS 配置](#aws-配置)
- [工作流说明](#工作流说明)
- [使用指南](#使用指南)
- [故障排除](#故障排除)

---

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline Architecture                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Git Push/PR                                                  │
│      ↓                                                        │
│  ┌─────────────┐                                             │
│  │  ci.yml     │ → Code Quality, Tests, Security Scan        │
│  │  pr-check   │ → PR Validation, Coverage Report            │
│  └─────────────┘                                             │
│      ↓                                                        │
│  ┌─────────────────────────────────────────────┐             │
│  │  Manual Trigger or Auto Deploy              │             │
│  └─────────────────────────────────────────────┘             │
│      ↓                              ↓                         │
│  ┌─────────────┐            ┌─────────────┐                 │
│  │ Lambda      │            │  Agent      │                  │
│  │ Deployment  │            │  Runtime    │                  │
│  └─────────────┘            └─────────────┘                 │
│      ↓                              ↓                         │
│  ┌────────┐  ┌─────────┐  ┌────────┐                       │
│  │  DEV   │→ │ STAGING │→ │  PROD  │                       │
│  └────────┘  └─────────┘  └────────┘                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 前置要求

### 1. GitHub 仓库设置

确保你的仓库有以下权限：
- Actions: Read and write permissions
- Pull requests: Allow workflows to create and approve pull requests

### 2. AWS 账号准备

需要准备 3 个 AWS 环境（可选，根据实际需求调整）：
- **DEV** - 开发环境
- **STAGING** - 预发布环境
- **PROD** - 生产环境

每个环境需要独立的 IAM 用户或角色，具备以下权限：
- Lambda 完整权限
- IAM Role 创建/管理权限
- ECR 推送权限
- Bedrock AgentCore 部署权限
- SSM Parameter Store 读取权限

---

## 🔐 GitHub 配置

### Step 1: 配置 GitHub Secrets

进入仓库 **Settings → Secrets and variables → Actions**，添加以下 secrets：

#### DEV 环境
```
AWS_ACCESS_KEY_ID_DEV
AWS_SECRET_ACCESS_KEY_DEV
```

#### STAGING 环境
```
AWS_ACCESS_KEY_ID_STAGING
AWS_SECRET_ACCESS_KEY_STAGING
```

#### PROD 环境
```
AWS_ACCESS_KEY_ID_PROD
AWS_SECRET_ACCESS_KEY_PROD
```

### Step 2: 配置 GitHub Environments

1. 进入 **Settings → Environments**
2. 创建 3 个环境：`dev`, `staging`, `production`

#### DEV 环境配置
- **Protection rules**: 无需审批
- **Deployment branches**: All branches

#### STAGING 环境配置
- **Protection rules**: 可选审批
- **Deployment branches**: main, develop

#### PROD 环境配置
- **Protection rules**:
  - ✅ Required reviewers (至少 1 人)
  - ✅ Wait timer: 5 minutes
- **Deployment branches**: main only
- **Environment secrets**: 使用 PROD 的 AWS credentials

---

## ☁️ AWS 配置

### 1. IAM 策略模板

为 CI/CD 创建专用 IAM 策略：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaDeployment",
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:GetFunction",
        "lambda:PublishVersion",
        "lambda:AddPermission"
      ],
      "Resource": "arn:aws:lambda:us-east-1:*:function:aws-support-tools-*"
    },
    {
      "Sid": "IAMRoleManagement",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:GetRole",
        "iam:PutRolePolicy",
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::*:role/aws-support-lambda-*"
    },
    {
      "Sid": "ECRAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Sid": "BedrockAgentCore",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SSMParameterStore",
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:us-east-1:*:parameter/support/*"
    }
  ]
}
```

### 2. 创建 IAM 用户

为每个环境创建独立的 IAM 用户：

```bash
# DEV 环境
aws iam create-user --user-name github-actions-dev
aws iam attach-user-policy --user-name github-actions-dev --policy-arn <policy-arn>
aws iam create-access-key --user-name github-actions-dev

# STAGING 环境
aws iam create-user --user-name github-actions-staging
aws iam attach-user-policy --user-name github-actions-staging --policy-arn <policy-arn>
aws iam create-access-key --user-name github-actions-staging

# PROD 环境
aws iam create-user --user-name github-actions-prod
aws iam attach-user-policy --user-name github-actions-prod --policy-arn <policy-arn>
aws iam create-access-key --user-name github-actions-prod
```

### 3. 配置 SSM Parameters

在每个环境中设置 SSM 参数：

```bash
# DEV 环境
aws ssm put-parameter \
  --name /support/agentgateway/aws_support_gateway_dev \
  --value "https://gateway-dev.bedrock-agentcore.us-east-1.amazonaws.com" \
  --type String

aws ssm put-parameter \
  --name /support/knowledge_base/kb_id_dev \
  --value "KB123456" \
  --type String

# STAGING 和 PROD 类似...
```

---

## 📋 工作流说明

### 1. `ci.yml` - 持续集成

**触发条件:**
- Push 到 `main` 或 `develop` 分支
- Pull Request 到 `main` 或 `develop`

**执行内容:**
- ✅ 代码格式检查 (Ruff, Black)
- ✅ 类型检查 (mypy)
- ✅ Lambda 函数验证
- ✅ Agent 模块验证
- ✅ 安全漏洞扫描
- ✅ JSON/YAML 配置验证
- ✅ 敏感信息检查

**何时使用:** 自动触发，无需手动操作

---

### 2. `deploy-lambda.yml` - Lambda 部署

**触发条件:**
- Push 到 `main` 分支（自动部署到 DEV）
- 手动触发 (workflow_dispatch)

**执行流程:**
1. 验证 Lambda handler
2. 检查工具名称长度
3. 部署到目标环境
4. 运行测试

**使用方法:**

#### 自动部署 (DEV)
```bash
git push origin main  # 自动触发部署到 DEV
```

#### 手动部署
1. 进入 GitHub Actions 页面
2. 选择 "Deploy Lambda to AWS"
3. 点击 "Run workflow"
4. 选择环境: `dev` / `staging` / `prod`
5. (可选) 自定义 Lambda 函数名
6. 点击 "Run workflow"

**环境变量覆盖:**

可以通过修改 `deploy_lambda.py` 支持环境变量：

```python
# deploy_lambda.py
LAMBDA_FUNCTION_NAME = os.environ.get(
    'LAMBDA_FUNCTION_NAME',
    'aws-support-tools-lambda'
)
```

---

### 3. `deploy-agent.yml` - Agent Runtime 部署

**触发条件:**
- Push 到 `main` 分支，且修改了 Agent 代码
- 手动触发

**执行流程:**
1. 验证 Agent 代码
2. 构建 Docker 镜像
3. 推送到 ECR
4. 部署到 AgentCore Runtime
5. 运行烟雾测试

**使用方法:**

```bash
# 进入 Actions → Deploy Agent Runtime to AWS
# 选择环境并运行
```

**注意事项:**
- 首次部署需要手动创建 ECR repository
- 确保 `.bedrock_agentcore.yaml` 配置正确
- PROD 部署需要审批

---

### 4. `pr-check.yml` - PR 质量检查

**触发条件:**
- Pull Request 创建/更新

**检查内容:**
- PR 标题格式 (semantic commit)
- PR 大小警告
- 代码变更影响分析
- 依赖变更检测
- 敏感信息扫描
- 测试覆盖率报告
- 自动代码审查

**PR 标题规范:**

```
<type>: <description>

类型 (type):
- feat: 新功能
- fix: Bug 修复
- docs: 文档更新
- refactor: 重构
- perf: 性能优化
- test: 测试
- ci: CI/CD 配置
- chore: 其他变更

示例:
✅ feat: add support for multiple languages in agent
✅ fix: resolve lambda timeout issue
✅ docs: update deployment guide
❌ update code (缺少类型)
❌ WIP: testing (不应该用 WIP)
```

---

### 5. `dependency-update.yml` - 依赖更新

**触发条件:**
- 每周一上午 9:00 (北京时间)
- 手动触发

**执行内容:**
- 安全漏洞扫描 (safety, pip-audit)
- 检查过时依赖
- 如果发现漏洞，自动创建 Issue

**手动运行:**
```bash
# Actions → Dependency Updates → Run workflow
```

---

## 🚀 使用指南

### 场景 1: 修复 Lambda Bug 并快速发布到生产

```bash
# 1. 创建分支
git checkout -b fix/lambda-timeout

# 2. 修复代码
vim 02_AWS_Support_Case_Lambda/lambda_handler.py

# 3. 提交
git add .
git commit -m "fix: increase lambda timeout to 120s"
git push origin fix/lambda-timeout

# 4. 创建 PR (触发 pr-check.yml)
gh pr create --title "fix: increase lambda timeout to 120s"

# 5. PR 合并后自动部署到 DEV

# 6. 手动部署到 STAGING 测试
# Actions → Deploy Lambda → Run workflow → Select "staging"

# 7. 测试通过后部署到 PROD
# Actions → Deploy Lambda → Run workflow → Select "prod"
# (需要等待审批)
```

---

### 场景 2: 更新 Agent System Prompt

```bash
# 1. 修改 Agent 代码
vim 04_create_knowledge_mcp_gateway_Agent/aws_support_agent.py

# 2. 本地测试
export INIT_MODE=lazy
python -c "import aws_support_agent"

# 3. 提交并推送
git add .
git commit -m "feat: improve agent system prompt for e-commerce"
git push origin main

# 4. 自动触发 CI 和 DEV 部署

# 5. 手动部署到 PROD
# Actions → Deploy Agent Runtime → Select "prod"
```

---

### 场景 3: 安全漏洞修复

```bash
# 1. 查看依赖更新 workflow 创建的 Issue

# 2. 更新依赖
cd 04_create_knowledge_mcp_gateway_Agent
uv pip install --upgrade <package>
uv pip freeze > requirements.txt

# 3. 测试
pytest tests/

# 4. 提交
git add requirements.txt
git commit -m "chore(deps): upgrade boto3 to fix CVE-2024-XXXXX"
git push origin main

# 5. 通过 PR 流程部署
```

---

## 🔍 故障排除

### 问题 1: Lambda 部署失败 - IAM Role 不存在

**错误信息:**
```
Error: Role arn:aws:iam::xxx:role/aws-support-lambda-execution-role does not exist
```

**解决方案:**
```bash
# deploy_lambda.py 会自动创建 Role
# 如果失败，手动创建:
aws iam create-role \
  --role-name aws-support-lambda-execution-role \
  --assume-role-policy-document file://trust-policy.json
```

---

### 问题 2: ECR 推送失败

**错误信息:**
```
Error: Repository does not exist
```

**解决方案:**
```bash
# 创建 ECR repository
aws ecr create-repository \
  --repository-name aws-support-agent \
  --region us-east-1
```

---

### 问题 3: Secrets 未配置

**错误信息:**
```
Error: AWS credentials not configured
```

**解决方案:**
1. 进入 Settings → Secrets and variables → Actions
2. 添加 `AWS_ACCESS_KEY_ID_DEV` 和 `AWS_SECRET_ACCESS_KEY_DEV`
3. 重新运行 workflow

---

### 问题 4: PR 检查失败 - 标题格式不正确

**错误信息:**
```
❌ PR title does not match conventional commit format
```

**解决方案:**
```bash
# 修改 PR 标题为:
feat: add new feature
fix: resolve bug
docs: update README
```

---

## 📊 监控和日志

### CloudWatch Logs

查看 Lambda 日志:
```bash
aws logs tail /aws/lambda/aws-support-tools-lambda-prod --follow
```

### GitHub Actions 日志

- 进入 **Actions** 标签
- 选择对应的 workflow run
- 查看详细日志和 artifacts

### 部署历史

查看 Lambda 版本:
```bash
aws lambda list-versions-by-function \
  --function-name aws-support-tools-lambda-prod
```

---

## 🔄 回滚操作

### Lambda 回滚

```bash
# 查看版本列表
aws lambda list-versions-by-function \
  --function-name aws-support-tools-lambda-prod

# 回滚到特定版本
aws lambda update-alias \
  --function-name aws-support-tools-lambda-prod \
  --name PROD \
  --function-version <version-number>
```

### Agent Runtime 回滚

```bash
# 重新部署之前的 Docker 镜像
# Actions → Deploy Agent Runtime → Use previous image tag
```

---

## 📚 最佳实践

1. **小步快跑**: 每次 PR 只做一件事
2. **先测后部署**: DEV → STAGING → PROD
3. **代码审查**: 所有 PR 需要至少 1 人审批
4. **自动化测试**: 在 PR 阶段就发现问题
5. **版本标签**: 生产部署后打 Git tag

```bash
# 生产发布后打标签
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
```

6. **监控告警**: 部署后密切关注 CloudWatch Metrics
7. **文档更新**: 重大变更同步更新文档

---

## 🎯 下一步

- [ ] 配置 Slack/钉钉通知集成
- [ ] 添加性能测试自动化
- [ ] 配置 Terraform/CloudFormation IaC
- [ ] 实现蓝绿部署策略
- [ ] 添加 Canary 发布流程

---

## 📞 支持

遇到问题？
1. 查看本文档故障排除部分
2. 检查 GitHub Actions 日志
3. 创建 Issue 寻求帮助
