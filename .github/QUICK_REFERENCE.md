# CI/CD 快速参考

## 🚀 常用命令

### 本地测试
```bash
# 运行本地 CI 检查
./.github/scripts/local-ci-test.sh

# 自动修复格式问题
./.github/scripts/local-ci-test.sh --fix

# 格式化代码
black 02_AWS_Support_Case_Lambda/ 04_create_knowledge_mcp_gateway_Agent/

# Lint 检查
ruff check .

# 类型检查
mypy 02_AWS_Support_Case_Lambda/lambda_handler.py --ignore-missing-imports

# 安全扫描
safety check -r 04_create_knowledge_mcp_gateway_Agent/requirements.txt
```

---

## 📦 部署流程

### Lambda 部署

#### 方法 1: GitHub Actions (推荐)
```
1. 进入 Actions → "Deploy Lambda to AWS"
2. 点击 "Run workflow"
3. 选择环境: dev / staging / prod
4. 点击 "Run workflow"
```

#### 方法 2: 本地部署
```bash
cd 02_AWS_Support_Case_Lambda
python deploy_lambda.py
```

---

### Agent Runtime 部署

```
1. 进入 Actions → "Deploy Agent Runtime to AWS"
2. 点击 "Run workflow"
3. 选择环境: dev / staging / prod
4. (可选) 勾选 "Force rebuild"
5. 点击 "Run workflow"
```

---

## 🔄 Git 工作流

### 功能开发
```bash
# 1. 创建功能分支
git checkout -b feat/your-feature

# 2. 开发和提交
git add .
git commit -m "feat: add new feature"

# 3. 推送并创建 PR
git push origin feat/your-feature
gh pr create --title "feat: add new feature"

# 4. PR 合并后自动部署到 DEV
```

### Bug 修复
```bash
# 1. 创建修复分支
git checkout -b fix/bug-description

# 2. 修复并提交
git add .
git commit -m "fix: resolve issue with X"

# 3. 推送并创建 PR
git push origin fix/bug-description
gh pr create --title "fix: resolve issue with X"
```

### 紧急热修复
```bash
# 1. 从 main 创建分支
git checkout -b hotfix/critical-fix main

# 2. 修复
git add .
git commit -m "hotfix: critical security fix"

# 3. 推送
git push origin hotfix/critical-fix

# 4. 创建 PR 并标记为紧急
gh pr create --title "hotfix: critical security fix" --label "priority:high"

# 5. 合并后手动触发 PROD 部署
```

---

## 📋 PR 检查清单

在创建 PR 前确认：

- [ ] PR 标题符合规范 (`feat:`, `fix:`, `docs:`, etc.)
- [ ] 本地 CI 测试通过 (`./.github/scripts/local-ci-test.sh`)
- [ ] 代码已格式化 (`black`)
- [ ] 没有 linting 错误 (`ruff`)
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] 没有敏感信息 (账户ID, access key)
- [ ] PR 描述清晰

---

## 🔐 Secrets 配置

### GitHub Secrets 列表

| Secret | 用途 | 环境 |
|--------|------|------|
| `AWS_ACCESS_KEY_ID_DEV` | AWS 认证 | DEV |
| `AWS_SECRET_ACCESS_KEY_DEV` | AWS 认证 | DEV |
| `AWS_ACCESS_KEY_ID_STAGING` | AWS 认证 | STAGING |
| `AWS_SECRET_ACCESS_KEY_STAGING` | AWS 认证 | STAGING |
| `AWS_ACCESS_KEY_ID_PROD` | AWS 认证 | PROD |
| `AWS_SECRET_ACCESS_KEY_PROD` | AWS 认证 | PROD |

### 配置路径
```
Settings → Secrets and variables → Actions → New repository secret
```

---

## 🛠️ 故障排除

### Lambda 部署失败

```bash
# 检查 IAM Role
aws iam get-role --role-name aws-support-lambda-execution-role

# 查看 Lambda 函数
aws lambda get-function --function-name aws-support-tools-lambda-dev

# 查看日志
aws logs tail /aws/lambda/aws-support-tools-lambda-dev --follow
```

### Agent 部署失败

```bash
# 检查 ECR repository
aws ecr describe-repositories --repository-names aws-support-agent

# 查看最近的镜像
aws ecr list-images --repository-name aws-support-agent

# 检查 AgentCore Runtime
aws bedrock-agentcore list-agents --region us-east-1
```

### PR 检查失败

```bash
# 本地运行相同的检查
./.github/scripts/local-ci-test.sh

# 查看具体错误
# Actions → 失败的 workflow → 展开失败的步骤
```

---

## 📊 监控和日志

### CloudWatch Logs

```bash
# Lambda 日志
aws logs tail /aws/lambda/aws-support-tools-lambda-prod --follow

# 过滤错误
aws logs filter-log-events \
  --log-group-name /aws/lambda/aws-support-tools-lambda-prod \
  --filter-pattern "ERROR"

# 查看特定时间段
aws logs filter-log-events \
  --log-group-name /aws/lambda/aws-support-tools-lambda-prod \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

### CloudWatch Metrics

```bash
# Lambda 调用次数
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=aws-support-tools-lambda-prod \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Lambda 错误率
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=aws-support-tools-lambda-prod \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

---

## 🔄 回滚操作

### Lambda 回滚

```bash
# 1. 查看版本历史
aws lambda list-versions-by-function \
  --function-name aws-support-tools-lambda-prod

# 2. 回滚到特定版本
aws lambda update-alias \
  --function-name aws-support-tools-lambda-prod \
  --name PROD \
  --function-version <version-number>

# 3. 验证
aws lambda get-function \
  --function-name aws-support-tools-lambda-prod \
  --qualifier PROD
```

### Agent Runtime 回滚

```bash
# 通过 GitHub Actions 重新部署旧版本
# Actions → Deploy Agent Runtime → Use previous image tag
# 或者手动指定镜像标签
```

---

## 📞 获取帮助

### 查看日志
```bash
# GitHub Actions 日志
# 进入 Actions → 选择 workflow → 查看详细日志

# 下载 workflow artifacts
gh run download <run-id>
```

### 调试技巧

1. **启用详细日志**
   ```yaml
   # 在 workflow 中添加
   env:
     ACTIONS_STEP_DEBUG: true
   ```

2. **SSH 到 GitHub Actions runner**
   ```yaml
   # 添加到 workflow step
   - name: Setup tmate session
     uses: mxschmitt/action-tmate@v3
   ```

3. **本地运行 GitHub Actions**
   ```bash
   # 使用 act 工具
   brew install act
   act -l  # 列出所有 jobs
   act -j test-lambda  # 运行特定 job
   ```

---

## 🎯 最佳实践

1. **提交前检查**
   - 运行本地 CI: `./.github/scripts/local-ci-test.sh`
   - 确保测试通过

2. **小步快跑**
   - 每个 PR 只做一件事
   - 保持 PR 小于 500 行

3. **环境隔离**
   - DEV → STAGING → PROD
   - 生产部署需要审批

4. **监控告警**
   - 部署后检查 CloudWatch
   - 设置错误率告警

5. **文档同步**
   - 代码变更同步更新文档
   - PR 包含文档更新

---

## 🔗 相关链接

- [完整 CI/CD 配置指南](.github/CICD_SETUP.md)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [AWS Lambda 文档](https://docs.aws.amazon.com/lambda/)
- [Bedrock AgentCore 文档](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
