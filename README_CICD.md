# CI/CD 架构总结

> **混合架构**: 基础设施手动（SageMaker Notebook） + 应用代码自动（GitHub Actions）

---

## 🎯 一句话总结

**Lambda 改代码自动部署，基础设施在 Notebook 手动执行** ✅

---

## 📊 架构图

```
┌─────────────────────────────────────────────────────┐
│               GitHub Repository                      │
│  📁 Lambda Code (频繁变更)                           │
│  📁 Agent Code (偶尔变更)                            │
│  📁 Infrastructure Notebooks (参考)                  │
└─────────────────────────────────────────────────────┘
         │                                │
         │ git push                       │ git pull
         ↓                                ↓
┌─────────────────────┐      ┌──────────────────────┐
│  GitHub Actions     │      │  SageMaker Notebook  │
│  (自动触发)         │      │  (手动执行)          │
│                     │      │                      │
│  ✓ 代码检查         │      │  ✓ Knowledge Base   │
│  ✓ Lambda 部署      │      │  ✓ Gateway          │
│  ✓ 安全扫描         │      │  ✓ Agent Runtime    │
│  ✓ PR 审查          │      │  ✓ 交互式调试        │
└─────────────────────┘      └──────────────────────┘
         │                                │
         └────────────┬───────────────────┘
                      ↓
         ┌─────────────────────────────┐
         │        AWS 环境              │
         │                             │
         │  ⚡ Lambda Functions        │
         │  📚 Knowledge Base          │
         │  🚪 AgentCore Gateway       │
         │  🤖 Agent Runtime           │
         └─────────────────────────────┘
```

---

## 🔄 工作流对比

| 操作 | 方式 | 时间 | 频率 |
|------|------|------|------|
| **Lambda bug fix** | 📝 改代码 → 🚀 自动部署 | 5 分钟 | 高（每天） |
| **Agent prompt 优化** | 📝 改代码 → 📓 Notebook 部署 | 15 分钟 | 中（每周） |
| **Gateway 新工具** | 📝 Lambda 自动 → 📓 Gateway 手动 | 20 分钟 | 低（每月） |
| **Knowledge Base 更新** | 📓 Notebook 同步 | 30 分钟 | 低（每月） |
| **初次搭建环境** | 📓 Notebook 全流程 | 60 分钟 | 极低（一次） |

---

## 📁 文件导航

### 🚀 快速开始
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** ⭐⭐⭐⭐⭐
  - 完整部署流程
  - 日常场景示例
  - 环境管理
  - 故障排除

### 📓 SageMaker 相关
- **[SAGEMAKER_NOTEBOOK_CHECKLIST.md](SAGEMAKER_NOTEBOOK_CHECKLIST.md)** ⭐⭐⭐⭐⭐
  - Notebook 执行清单
  - 分步操作指南
  - 输出验证
  - 问题排查

### ⚙️ GitHub Actions
- **[.github/workflows/ci.yml](.github/workflows/ci.yml)** - 代码质量检查
- **[.github/workflows/deploy-lambda.yml](.github/workflows/deploy-lambda.yml)** - Lambda 自动部署 ⭐
- **[.github/workflows/pr-check.yml](.github/workflows/pr-check.yml)** - PR 质量把关
- **[.github/workflows/deploy-agent.yml](.github/workflows/deploy-agent.yml)** - 仅供参考
- **[.github/workflows/update-agent-code.yml](.github/workflows/update-agent-code.yml)** - 变更通知

### 📚 参考文档
- **[.github/CICD_SETUP.md](.github/CICD_SETUP.md)** - GitHub Actions 详细配置
- **[.github/QUICK_REFERENCE.md](.github/QUICK_REFERENCE.md)** - 常用命令速查
- **[.github/CICD_COMPARISON.md](.github/CICD_COMPARISON.md)** - 方案对比
- **[aws-cicd/NOTEBOOK_CICD_STRATEGY.md](aws-cicd/NOTEBOOK_CICD_STRATEGY.md)** - Notebook CI/CD 策略

---

## ✅ 配置状态

### 已完成 ✅
- [x] GitHub Actions workflows (5 个)
- [x] Lambda 自动部署流程
- [x] PR 质量检查
- [x] 代码安全扫描
- [x] Dependabot 依赖更新
- [x] 本地 CI 测试脚本
- [x] 完整文档体系

### 需要配置 ⚠️
- [ ] GitHub Secrets (AWS 凭证)
- [ ] GitHub Environments (dev/staging/prod)
- [ ] SageMaker Notebook Instance
- [ ] 首次基础设施部署

### 可选配置 💡
- [ ] Slack/钉钉通知集成
- [ ] CloudWatch 告警
- [ ] Terraform/CDK IaC
- [ ] 蓝绿部署

---

## 🎯 使用指南

### Scenario 1: 我要修复一个 Lambda Bug

```bash
# 1. 改代码
vim 02_AWS_Support_Case_Lambda/lambda_handler.py

# 2. 提交
git add .
git commit -m "fix: handle timeout gracefully"
git push

# 3. 自动部署到 DEV ✅
# 查看: GitHub Actions → Deploy Lambda to AWS

# 4. 部署到 PROD
# Actions → Deploy Lambda → Run workflow → Select "prod"
```

**不需要**:
- ❌ 打开 SageMaker Notebook
- ❌ 手动执行任何脚本
- ❌ 配置 AWS CLI

---

### Scenario 2: 我要优化 Agent 的回答

```bash
# 1. 改代码
vim 04_create_knowledge_mcp_gateway_Agent/aws_support_agent.py
# 修改 get_system_prompt() 函数

# 2. 提交
git commit -m "feat: improve agent prompt for billing questions"
git push

# 3. 在 SageMaker Notebook 中
cd ~/SageMaker/aws-omni-support-agent
git pull
# 打开 deploy_QA_agent.ipynb
# 执行 Cell 14-17（部署 Runtime）

# 4. 测试
python agent_client.py
```

**需要**:
- ✅ SageMaker Notebook
- ✅ 手动执行部分 cells
- ✅ 验证部署

---

### Scenario 3: 初次搭建环境

**参考**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#初次部署完整清单)

**步骤**:
1. 启动 SageMaker Notebook
2. 执行 3 个 Notebooks（顺序执行）
3. 配置 GitHub Secrets
4. 触发 Lambda 首次部署

**时间**: 约 1-1.5 小时

---

## 🔐 安全性

### 已实现 ✅
- ✅ GitHub Secrets 存储 AWS 凭证
- ✅ 生产环境需要审批
- ✅ 依赖安全扫描（Safety）
- ✅ 敏感信息检测（Gitleaks）
- ✅ `.gitignore` 排除敏感文件
- ✅ IAM Role 最小权限

### 最佳实践 💡
- 定期轮换 AWS 凭证
- 使用 Secrets Manager 管理敏感配置
- 生产部署前代码审查
- 监控 CloudWatch Logs

---

## 💰 成本估算

### GitHub Actions
```
公开仓库: 免费
私有仓库: 2000 分钟/月免费
你的用量: ~450 分钟/月
成本: $0
```

### SageMaker Notebook
```
实例类型: ml.t3.medium
费率: $0.0582/小时
假设用量: 每天 2 小时 = $3.49/月
```

### 总计
```
~$3.5/月（仅 SageMaker）
```

**对比纯 AWS 方案**: 节省约 ~$5/月

---

## 🚀 快速命令

### 本地开发
```bash
# 运行本地 CI 检查
./.github/scripts/local-ci-test.sh

# 自动修复格式
./.github/scripts/local-ci-test.sh --fix

# 验证 Lambda
cd 02_AWS_Support_Case_Lambda
python -c "import lambda_handler"

# 验证 Agent
cd 04_create_knowledge_mcp_gateway_Agent
export INIT_MODE=lazy && python -c "import aws_support_agent"
```

### AWS 操作
```bash
# 查看 Lambda 日志
aws logs tail /aws/lambda/aws-support-tools-lambda-prod --follow

# 测试 Lambda
aws lambda invoke --function-name aws-support-tools-lambda-dev \
  --payload '{"tool_name":"describe_severity_levels","parameters":{}}' output.json

# 查看 SSM 参数
aws ssm get-parameter --name /support/knowledge_base/kb_id_dev

# 验证 Agent
cd 04_create_knowledge_mcp_gateway_Agent && python agent_client.py
```

### Git 操作
```bash
# 创建功能分支
git checkout -b feat/new-tool

# 查看变更
git status
git diff

# 提交
git add .
git commit -m "feat: add new support tool"

# 推送并创建 PR
git push origin feat/new-tool
gh pr create --title "feat: add new support tool"
```

---

## 📞 获取帮助

### 文档查询顺序
1. 🔍 **先查**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. 🔍 **再查**: [SAGEMAKER_NOTEBOOK_CHECKLIST.md](SAGEMAKER_NOTEBOOK_CHECKLIST.md)
3. 🔍 **最后**: [.github/QUICK_REFERENCE.md](.github/QUICK_REFERENCE.md)

### 问题分类
- **Lambda 部署问题** → GitHub Actions 日志
- **Notebook 执行问题** → SageMaker Logs
- **Agent 运行问题** → CloudWatch Logs
- **权限问题** → IAM Policy

### 联系方式
- 创建 GitHub Issue
- 查看项目 Wiki
- 参考 AWS 官方文档

---

## 🎉 总结

你现在有了一个**生产级的混合 CI/CD 架构**：

✅ **Lambda 代码**: 全自动部署，快速迭代
✅ **基础设施**: SageMaker Notebook 手动执行，灵活可控
✅ **文档完善**: 清单式操作指南
✅ **成本优化**: 每月仅 ~$3.5
✅ **安全合规**: 多层防护

**下一步**:
1. 配置 GitHub Secrets
2. 首次部署基础设施（SageMaker）
3. 测试 Lambda 自动部署
4. 享受自动化带来的便利！🚀

---

**版本**: v1.0
**最后更新**: 2025-01-XX
**维护者**: percy-han
