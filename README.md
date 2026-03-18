# AWS Omni Support Agent

> 🤖 智能化 AWS 技术支持平台 - 结合 RAG 知识库和自动化工单管理的企业级 AI Agent

[![CI](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/ci.yml)
[![Deploy Lambda](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/deploy-lambda.yml/badge.svg)](https://github.com/percy-han/aws-omni-support-agent/actions/workflows/deploy-lambda.yml)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📖 目录

- [项目简介](#-项目简介)
- [核心特性](#-核心特性)
- [系统架构](#-系统架构)
- [业务流程](#-业务流程)
- [技术栈](#-技术栈)
- [快速开始](#-快速开始)
- [详细部署](#-详细部署)
- [使用指南](#-使用指南)
- [项目结构](#-项目结构)
- [CI/CD](#-cicd)
- [常见问题](#-常见问题)
- [贡献指南](#-贡献指南)
- [License](#-license)

---

## 🎯 项目简介

AWS Omni Support Agent 是一个**企业级智能支持平台**，专为跨境电商 IT 团队设计，提供以下核心能力：

### 问题解决
- ✅ **智能问答**: 基于 RAG（检索增强生成）的 AWS 技术问答
- ✅ **知识库集成**: AWS 官方文档 + 企业内部知识沉淀
- ✅ **多语言支持**: 中文优先，支持英文

### 工单管理
- ✅ **自动化工单**: 创建、查询、更新、关闭 AWS Support Cases
- ✅ **智能路由**: 根据问题严重程度自动分级
- ✅ **全流程追踪**: 从创建到解决的完整生命周期管理

### 业务集成
- ✅ **电商场景优化**: 针对支付、订单、库存等关键场景定制
- ✅ **业务影响评估**: 自动关联技术问题与业务影响
- ✅ **峰值优先级**: 购物节期间自动提升问题优先级

---

## ✨ 核心特性

### 1. 混合架构设计

| 组件 | 架构 | 优势 |
|------|------|------|
| **应用层** | Lambda + AgentCore Gateway | 40-60% 成本降低，自动扩展 |
| **AI 层** | Claude Opus 4.5 + Bedrock | 最先进的推理能力 |
| **知识层** | OpenSearch + Titan Embeddings | 毫秒级检索 |
| **部署层** | GitHub Actions + SageMaker | 混合 CI/CD，灵活高效 |

### 2. 企业级可靠性

```
🔒 安全性
  ├─ IAM Role 原生认证（无需管理密钥）
  ├─ 多环境隔离（DEV/STAGING/PROD）
  ├─ 敏感信息检测（Gitleaks + git-secrets）
  └─ 依赖安全扫描（Safety + pip-audit）

⚡ 性能
  ├─ Eager 初始化（减少冷启动）
  ├─ 连接池复用
  ├─ 智能重试机制
  └─ 区域自动检测

📊 可观测性
  ├─ 结构化日志（CloudWatch）
  ├─ 性能指标（Lambda Metrics）
  ├─ 错误追踪（X-Ray 集成）
  └─ 部署记录（GitHub Actions）
```

### 3. 开发者友好

- 📝 **完整文档**: 10+ 详细文档，覆盖所有场景
- 🧪 **本地测试**: 提交前在本地运行 CI 检查
- 🔄 **自动化部署**: Lambda 代码 5 分钟自动部署
- 📓 **交互式开发**: SageMaker Notebook 快速迭代

---

## 🏗️ 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户交互层                            │
│  Slack / 钉钉 / Web UI / CLI                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent 运行时                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  AWS Support Agent (Claude Opus 4.5)                │  │
│  │  - System Prompt (320 行业务逻辑)                   │  │
│  │  - 双阶段查询（知识库 → AWS 文档 → 工单）          │  │
│  │  - 中文优先 + 电商场景优化                          │  │
│  └──────────────────────────────────────────────────────┘  │
│         ↓                    ↓                    ↓          │
│  ┌──────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │Knowledge │      │ AgentCore    │      │ MCP Client   │ │
│  │Base(RAG) │      │ Gateway      │      │ (AWS Docs)   │ │
│  └──────────┘      └──────────────┘      └──────────────┘ │
│         ↓                    ↓                              │
│  ┌──────────┐      ┌──────────────┐                       │
│  │OpenSearch│      │ Lambda       │                       │
│  │+ Titan   │      │ (7 Tools)    │                       │
│  └──────────┘      └──────────────┘                       │
│                             ↓                               │
│                    ┌──────────────┐                        │
│                    │ AWS Support  │                        │
│                    │ API          │                        │
│                    └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### 架构演进

#### 旧架构（已废弃）
```
Agent Runtime → Gateway → MCP Runtime → Support API
                           (Cognito 认证)
```
**问题**:
- 复杂度高（2 个 Runtime）
- 成本高（持续运行）
- Token 刷新管理复杂

#### 新架构（当前）
```
Agent Runtime → Gateway → Lambda → Support API
                          (IAM Role)
```
**优势**:
- ✅ 成本降低 40-60%
- ✅ 认证简化（原生 IAM）
- ✅ 自动扩展
- ✅ 运维简单

---

## 🔄 业务流程

### Flow 1: 技术问答（智能检索）

```
用户提问: "如何优化 Lambda 冷启动？"
    ↓
1️⃣ 知识库检索
    ├─ 查询企业知识库（RAG）
    ├─ 返回相关文档片段
    └─ 计算相似度分数
    ↓
2️⃣ 评估结果质量
    ├─ 如果找到高质量答案 → 直接回答 ✅
    ├─ 如果部分匹配 → 继续 AWS 文档检索
    └─ 如果无结果 → 进入第 3 步
    ↓
3️⃣ AWS 官方文档检索
    ├─ MCP Client 查询 AWS Docs
    ├─ 综合知识库 + 官方文档
    └─ 生成答案
    ↓
4️⃣ 回答 + 置信度
    ├─ 答案内容（Markdown 格式）
    ├─ 来源引用（知识库/官方文档）
    ├─ 置信度评分（高/中/低）
    └─ 如果置信度低 → 建议创建工单
```

### Flow 2: 工单管理（全自动）

```
用户: "帮我开个 case，EC2 实例无法启动"
    ↓
1️⃣ 信息收集
    ├─ 问题描述
    ├─ 严重程度评估（根据业务影响）
    ├─ 服务类型识别
    └─ 所需附件
    ↓
2️⃣ 自动创建工单
    ├─ 调用 create_support_case
    ├─ 设置严重级别（critical/urgent/high/normal/low）
    ├─ 填充详细信息
    └─ 返回 Case ID
    ↓
3️⃣ 跟踪工单
    ├─ 定期查询状态（describe_support_cases）
    ├─ 读取 AWS 工程师回复
    ├─ 提取关键信息
    └─ 通知用户
    ↓
4️⃣ 交互式处理
    ├─ 补充信息（add_communication_to_case）
    ├─ 上传附件（add_attachments_to_set）
    ├─ 问题解决后关闭（resolve_support_case）
    └─ 记录到知识库（闭环学习）
```

### Flow 3: 紧急响应（电商场景）

```
峰值期间（双11/黑五）检测到支付异常
    ↓
1️⃣ 自动升级优先级
    ├─ 检测时间窗口（购物节期间）
    ├─ 识别关键业务（支付/订单/库存）
    ├─ 自动设置为 CRITICAL
    └─ 绕过常规流程
    ↓
2️⃣ 快速诊断
    ├─ 查询历史相似问题
    ├─ 提供临时解决方案
    ├─ 并行创建紧急工单
    └─ 通知运维团队
    ↓
3️⃣ 持续跟踪
    ├─ 每 5 分钟查询状态
    ├─ 实时推送进展
    ├─ 协调 AWS TAM（如有）
    └─ 问题解决后生成事后分析报告
```

---

## 🛠️ 技术栈

### AI & ML
- **LLM**: Amazon Bedrock (Claude Opus 4.5)
- **Embeddings**: Amazon Titan Text Embeddings
- **Agent Framework**: Strands Agents
- **RAG Engine**: LangChain + OpenSearch

### AWS Services
- **Compute**: AWS Lambda, Amazon ECS (AgentCore Runtime)
- **Storage**: Amazon S3, Amazon OpenSearch Service
- **Integration**: Amazon Bedrock, AWS Support API
- **Gateway**: AWS Bedrock AgentCore Gateway
- **Secrets**: AWS Systems Manager Parameter Store
- **Monitoring**: Amazon CloudWatch

### Development & CI/CD
- **Language**: Python 3.11
- **Package Manager**: uv (pip-compatible)
- **CI/CD**: GitHub Actions (Lambda) + SageMaker Notebook (Infrastructure)
- **Testing**: pytest, moto, safety
- **Code Quality**: Ruff, Black, mypy

### Infrastructure as Code
- **Deployment**: Python scripts + CloudFormation (optional)
- **Configuration**: YAML, JSON, SSM Parameters

---

## 🚀 快速开始

### 前置要求

- **AWS 账户**: 商业或企业支持计划（用于 Support API）
- **Python**: 3.11+
- **AWS CLI**: 已配置凭证
- **Git**: 用于克隆仓库

### 5 分钟快速体验

```bash
# 1. 克隆仓库
git clone https://github.com/percy-han/aws-omni-support-agent.git
cd aws-omni-support-agent

# 2. 部署 Lambda 函数
cd 02_AWS_Support_Case_Lambda
pip install boto3
python deploy_lambda.py

# 3. 测试 Lambda
python test_lambda.py

# 4. 查看输出
# ✅ Lambda 部署成功
# ✅ 7 个工具可用
```

### 完整部署（60 分钟）

参考详细部署指南：

1. **基础设施部署**（SageMaker Notebook）
   - [SageMaker Notebook 执行清单](SAGEMAKER_NOTEBOOK_CHECKLIST.md)
   - 创建 Knowledge Base、Gateway、Agent Runtime

2. **应用代码部署**（GitHub Actions）
   - [CI/CD 配置指南](.github/CICD_SETUP.md)
   - 配置 Secrets、Environments

3. **验证部署**
   - [部署指南](DEPLOYMENT_GUIDE.md)

---

## 📚 详细部署

### 架构层次

| 层次 | 部署方式 | 频率 | 文档 |
|------|---------|------|------|
| **基础设施** | SageMaker Notebook | 偶尔（初次 + 重大变更） | [Notebook 清单](SAGEMAKER_NOTEBOOK_CHECKLIST.md) |
| **Lambda 代码** | GitHub Actions | 频繁（每次代码变更） | [Lambda 部署](.github/workflows/deploy-lambda.yml) |
| **Agent 代码** | SageMaker Notebook | 中等（优化 Prompt） | [Notebook 清单](SAGEMAKER_NOTEBOOK_CHECKLIST.md) |

### 环境配置

#### DEV 环境
```yaml
用途: 开发测试
自动部署: ✅ Lambda 自动，基础设施手动
数据: 测试数据
资源命名: *-dev
```

#### PROD 环境
```yaml
用途: 生产服务
自动部署: ⚠️ 需审批
数据: 真实数据
资源命名: *-prod
```

---

## 📖 使用指南

### 场景 1: 查询技术问题

```python
# 通过 Agent Client
from agent_client import test_invoke_agent

test_invoke_agent()
# 输入: "如何在 Lambda 中使用 VPC？"
# 输出: 详细的技术解答 + 官方文档链接 + 置信度
```

### 场景 2: 创建支持工单

```python
# Agent 会自动处理
user_input = """
帮我创建一个工单：
- 问题: EC2 实例 i-1234567890 无法启动
- 严重程度: urgent
- 服务: EC2
"""

# Agent 自动完成:
# 1. 收集必要信息
# 2. 调用 create_support_case
# 3. 返回 Case ID 和预计响应时间
```

### 场景 3: 查询工单状态

```python
user_input = "帮我查看一下过去一周的 support cases"

# Agent 响应:
# - 查询过去 7 天的工单
# - 按严重程度分组
# - 展示未解决的工单
# - 提供详细的进展信息
```

### 场景 4: 紧急问题处理

```python
user_input = """
紧急！生产环境支付网关无响应
- 时间: 双11 高峰期
- 影响: 无法完成支付
- 错误: Gateway Timeout
"""

# Agent 自动:
# 1. 识别为 CRITICAL 级别
# 2. 立即创建紧急工单
# 3. 查询知识库寻找快速解决方案
# 4. 提供临时 workaround
# 5. 持续跟踪工单进展
```

---

## 📁 项目结构

```
aws-omni-support-agent/
│
├── 01_create_support_knowledegbase_rag/    # 知识库 RAG 系统
│   ├── create_knowledge_base.ipynb         # 创建知识库 Notebook
│   ├── utils/                              # 工具函数
│   │   ├── knowledge_base.py               # KB 操作
│   │   ├── evaluation.py                   # RAG 评估
│   │   └── ...
│   ├── dataset/                            # 训练数据
│   └── requirements.txt                    # Python 依赖
│
├── 02_AWS_Support_Case_Lambda/             # Lambda 函数（7 个工具）
│   ├── lambda_handler.py                   # 主处理器 ⭐
│   ├── deploy_lambda.py                    # 自动部署脚本
│   ├── test_lambda.py                      # 测试脚本
│   ├── gateway_tools_schema.json           # 工具 Schema
│   ├── iam_policy.json                     # IAM 权限策略
│   └── requirements.txt                    # Python 依赖
│
├── 03_create_agentcore_gateway/            # Gateway 创建
│   └── create_agentcore_gateway.ipynb      # 创建 Gateway Notebook
│
├── 04_create_knowledge_mcp_gateway_Agent/  # Agent Runtime
│   ├── aws_support_agent.py                # Agent 核心代码 ⭐
│   ├── deploy_QA_agent.ipynb               # 部署 Notebook
│   ├── agent_client.py                     # 测试客户端
│   ├── streamable_http_sigv4.py            # SigV4 认证
│   ├── .bedrock_agentcore.yaml             # 配置文件（.gitignore）
│   └── requirements.txt                    # Python 依赖
│
├── .github/                                # GitHub Actions & Docs
│   ├── workflows/                          # CI/CD 工作流
│   │   ├── ci.yml                          # 持续集成
│   │   ├── deploy-lambda.yml               # Lambda 部署 ⭐
│   │   ├── pr-check.yml                    # PR 检查
│   │   ├── dependency-update.yml           # 依赖扫描
│   │   └── ...
│   ├── scripts/                            # 辅助脚本
│   │   └── local-ci-test.sh                # 本地 CI 测试
│   ├── CICD_SETUP.md                       # CI/CD 配置指南
│   ├── QUICK_REFERENCE.md                  # 快速参考
│   └── ...
│
├── aws-cicd/                               # AWS CI/CD 方案（参考）
│   ├── NOTEBOOK_CICD_STRATEGY.md           # Notebook CI/CD 策略
│   └── ARCHITECTURE_REEVALUATION.md        # 架构评估
│
├── scripts/                                # 项目脚本
│   └── cleanup_before_push.sh              # 推送前清理
│
├── DEPLOYMENT_GUIDE.md                     # 部署指南 ⭐
├── SAGEMAKER_NOTEBOOK_CHECKLIST.md         # Notebook 清单 ⭐
├── README_CICD.md                          # CI/CD 总结
├── README.md                               # 本文件
├── LICENSE                                 # 许可证
└── .gitignore                              # Git 忽略规则
```

### 核心文件说明

| 文件 | 用途 | 重要性 |
|------|------|--------|
| `lambda_handler.py` | Lambda 函数主逻辑，7 个工具实现 | ⭐⭐⭐⭐⭐ |
| `aws_support_agent.py` | Agent 核心，320 行 System Prompt | ⭐⭐⭐⭐⭐ |
| `deploy_lambda.py` | Lambda 自动部署脚本 | ⭐⭐⭐⭐ |
| `DEPLOYMENT_GUIDE.md` | 完整部署流程 | ⭐⭐⭐⭐⭐ |
| `deploy-lambda.yml` | Lambda CI/CD 工作流 | ⭐⭐⭐⭐ |

---

## 🔄 CI/CD

### 混合 CI/CD 架构

我们采用**混合架构**，平衡自动化和灵活性：

```
┌─────────────────────────────────┐
│ 基础设施（SageMaker Notebook）   │
│ - Knowledge Base                │
│ - Gateway                       │
│ - Agent Runtime                 │
│ 频率: 偶尔（手动）               │
└─────────────────────────────────┘
              ↓
┌─────────────────────────────────┐
│ 应用代码（GitHub Actions）       │
│ - Lambda 函数                   │
│ - 配置参数                      │
│ 频率: 频繁（自动）               │
└─────────────────────────────────┘
```

### 自动化工作流

| Workflow | 触发条件 | 功能 |
|----------|---------|------|
| **ci.yml** | Push/PR | 代码质量检查、安全扫描 |
| **deploy-lambda.yml** | Push to main | Lambda 自动部署 |
| **pr-check.yml** | PR 创建/更新 | PR 质量把关、自动审查 |
| **dependency-update.yml** | 每周一 | 依赖安全扫描 |

### 本地开发工作流

```bash
# 1. 修改代码
vim 02_AWS_Support_Case_Lambda/lambda_handler.py

# 2. 本地测试
./.github/scripts/local-ci-test.sh

# 3. 提交
git add .
git commit -m "feat: add new tool"

# 4. 推送（自动触发 CI/CD）
git push origin main

# 5. 查看部署进度
# GitHub → Actions → Deploy Lambda to AWS
```

### 生产部署流程

```
开发环境测试 → PR 审查 → 合并到 main → 自动部署 DEV
                                            ↓
                           手动触发 → 部署到 PROD（需审批）
```

详细配置参见：[CI/CD 配置指南](.github/CICD_SETUP.md)

---

## ❓ 常见问题

### Q1: 如何开始使用这个项目？

**A**: 分两步：
1. **快速体验**（5 分钟）：只部署 Lambda，体验工具函数
2. **完整部署**（60 分钟）：按照 [SAGEMAKER_NOTEBOOK_CHECKLIST.md](SAGEMAKER_NOTEBOOK_CHECKLIST.md) 部署全套系统

### Q2: 为什么使用混合 CI/CD（GitHub Actions + SageMaker）？

**A**:
- **基础设施**复杂且变更少，SageMaker Notebook 提供交互式调试
- **Lambda 代码**频繁更新，GitHub Actions 提供自动化部署
- **成本优化**：避免了 CodePipeline 的额外费用（节省 ~$5/月）

### Q3: 支持哪些 AWS Support 操作？

**A**: 7 个核心工具：
1. `create_support_case` - 创建工单
2. `describe_support_cases` - 查询工单
3. `add_communication_to_case` - 添加回复
4. `resolve_support_case` - 关闭工单
5. `describe_services` - 获取服务列表
6. `describe_severity_levels` - 获取严重级别
7. `add_attachments_to_set` - 上传附件

### Q4: 如何自定义 Agent 的行为？

**A**: 修改 `04_create_knowledge_mcp_gateway_Agent/aws_support_agent.py` 中的 `get_system_prompt()` 函数，该函数包含 320 行详细的业务逻辑。

### Q5: 成本是多少？

**A**:
- **GitHub Actions**: 免费（公开仓库）或在免费额度内
- **SageMaker Notebook**: ~$3.5/月（ml.t3.medium，每天 2 小时）
- **Lambda**: 按调用付费，~$0.004/月（假设每月 1000 次调用）
- **Bedrock**: 按 token 计费，根据实际使用量
- **总计**: ~$5-10/月（小规模使用）

### Q6: 如何回滚部署？

**A**:
- **Lambda**: 使用 AWS Lambda 版本别名回滚
- **Agent**: 在 SageMaker Notebook 中 git checkout 到之前的版本并重新部署

详细步骤参见：[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#-回滚操作)

### Q7: 支持哪些语言？

**A**:
- **Agent 输出**: 默认中文，支持英文
- **代码**: Python 3.11
- **文档**: 中英文混合（主要中文）

### Q8: 如何贡献代码？

**A**: 参见 [贡献指南](#-贡献指南)

---

## 🤝 贡献指南

我们欢迎任何形式的贡献！

### 贡献方式

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码

### 贡献流程

1. **Fork 仓库**
   ```bash
   # 在 GitHub 上 Fork 仓库
   git clone https://github.com/YOUR_USERNAME/aws-omni-support-agent.git
   ```

2. **创建功能分支**
   ```bash
   git checkout -b feat/your-feature
   ```

3. **开发和测试**
   ```bash
   # 本地测试
   ./.github/scripts/local-ci-test.sh

   # 运行测试
   cd 02_AWS_Support_Case_Lambda
   python -m pytest tests/
   ```

4. **提交代码**
   ```bash
   git add .
   git commit -m "feat: add your feature"
   git push origin feat/your-feature
   ```

5. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 等待 CI 检查通过
   - 回应 Code Review 意见

### Commit 规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat: 新功能
fix: Bug 修复
docs: 文档更新
refactor: 重构
perf: 性能优化
test: 测试相关
ci: CI/CD 配置
chore: 其他变更
```

### Code Review 清单

- [ ] 代码符合 PEP 8 规范
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] PR 描述清晰
- [ ] 无敏感信息泄露

---

## 📜 License

本项目采用 [MIT License](LICENSE)。

```
MIT License

Copyright (c) 2025 percy-han

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 📞 联系方式

- **GitHub Issues**: [提交 Issue](https://github.com/percy-han/aws-omni-support-agent/issues)
- **Discussions**: [参与讨论](https://github.com/percy-han/aws-omni-support-agent/discussions)
- **Email**: your-email@example.com

---

## 🙏 致谢

感谢以下开源项目和服务：

- [Amazon Bedrock](https://aws.amazon.com/bedrock/) - AI Foundation Models
- [Strands Agents](https://github.com/strands-ai/strands) - Agent Framework
- [LangChain](https://github.com/langchain-ai/langchain) - LLM Application Framework
- [GitHub Actions](https://github.com/features/actions) - CI/CD Platform

---

## 📈 项目统计

- **代码行数**: ~10,000 行
- **文档数量**: 15+ 篇
- **测试覆盖率**: TBD
- **部署时间**: 60 分钟（完整）/ 5 分钟（Lambda only）
- **维护团队**: 1-2 人

---

## 🗺️ Roadmap

### v1.0 (当前)
- [x] 基础 RAG 知识库
- [x] 7 个 Support API 工具
- [x] Agent Runtime 部署
- [x] Lambda 架构迁移
- [x] CI/CD 混合架构

### v1.1 (计划中)
- [ ] Slack 集成
- [ ] 钉钉集成
- [ ] 监控告警 Dashboard
- [ ] 工单分析报告

### v2.0 (未来)
- [ ] 多租户支持
- [ ] 自定义知识库
- [ ] 工单自动化规则引擎
- [ ] 移动端 App

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

Made with ❤️ by percy-han

</div>
