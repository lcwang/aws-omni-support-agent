# SageMaker Notebook CI/CD 策略

## 🎯 问题分析

你的部署流程依赖 **SageMaker Jupyter Notebooks**：
1. `create_knowledge_base.ipynb` - 创建知识库
2. `create_agentcore_gateway.ipynb` - 创建 Gateway
3. `deploy_QA_agent.ipynb` - 部署 Agent Runtime

**挑战**: GitHub Actions 无法直接在 SageMaker 环境中执行 Notebook

---

## 🏗️ 架构分析

### 当前架构
```
SageMaker Notebook
  ↓ (手动执行)
创建 Knowledge Base → 创建 Gateway → 部署 Agent Runtime
```

### 问题
- ❌ 无法自动化
- ❌ 依赖 SageMaker 环境
- ❌ 每次部署需要手动执行

---

## 💡 解决方案（4 种，推荐混合方案）

---

## 方案 1: 分层自动化（推荐）⭐⭐⭐⭐⭐

### 核心思路
**基础设施** (偶尔变更) + **应用代码** (频繁更新) 分开处理

### 架构
```
┌─────────────────────────────────────────────────┐
│ Infrastructure Layer (手动/半自动)               │
│ - Knowledge Base (偶尔创建)                     │
│ - Gateway (偶尔创建)                            │
│ - Agent Runtime (初次部署)                      │
│ 工具: SageMaker Notebook (手动)                 │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│ Application Layer (自动化)                      │
│ - Lambda 代码更新                               │
│ - Agent 代码更新（不重建容器）                   │
│ - 配置更新                                      │
│ 工具: GitHub Actions                            │
└─────────────────────────────────────────────────┘
```

### 实施步骤

#### Step 1: 基础设施部署（一次性/偶尔）
```bash
# 在 SageMaker Notebook 中手动执行
1. create_knowledge_base.ipynb    # 创建知识库
2. create_agentcore_gateway.ipynb # 创建 Gateway
3. deploy_QA_agent.ipynb          # 首次部署 Agent
```

#### Step 2: 应用代码自动更新（频繁）
```yaml
# GitHub Actions 自动执行
- Lambda 代码更新: deploy-lambda.yml
- Agent 代码热更新: update-agent-code.yml
- 配置更新: update-ssm-params.yml
```

### 优点
- ✅ 利用现有 Notebook 工作流
- ✅ 基础设施稳定后很少变更
- ✅ 应用代码快速迭代
- ✅ 低风险

### 缺点
- ⚠️ 基础设施变更仍需手动

---

## 方案 2: Notebook 转 Python 脚本 ⭐⭐⭐⭐

### 核心思路
将 Notebook 逻辑提取为可执行的 Python 脚本

### 实施步骤

#### Step 1: 导出 Notebook 为 Python
```bash
# 使用 nbconvert
jupyter nbconvert --to script deploy_QA_agent.ipynb

# 或使用 papermill 参数化
papermill deploy_QA_agent.ipynb output.ipynb \
  -p environment "prod" \
  -p region "us-east-1"
```

#### Step 2: 创建部署脚本
```python
# scripts/deploy_infrastructure.py
#!/usr/bin/env python3
"""
从 Notebook 提取的部署脚本
可被 GitHub Actions 调用
"""

def deploy_knowledge_base():
    # 从 create_knowledge_base.ipynb 提取的逻辑
    pass

def deploy_gateway():
    # 从 create_agentcore_gateway.ipynb 提取的逻辑
    pass

def deploy_agent_runtime():
    # 从 deploy_QA_agent.ipynb 提取的逻辑
    pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", choices=["kb", "gateway", "agent"])
    args = parser.parse_args()

    if args.component == "kb":
        deploy_knowledge_base()
    elif args.component == "gateway":
        deploy_gateway()
    elif args.component == "agent":
        deploy_agent_runtime()
```

#### Step 3: GitHub Actions 调用
```yaml
# .github/workflows/deploy-infrastructure.yml
- name: Deploy Knowledge Base
  run: python scripts/deploy_infrastructure.py --component kb
```

### 优点
- ✅ 完全自动化
- ✅ 可在 GitHub Actions 中执行
- ✅ 版本控制友好

### 缺点
- ⚠️ 需要重构 Notebook 代码
- ⚠️ 维护两套代码（Notebook + Script）

---

## 方案 3: Papermill + GitHub Actions ⭐⭐⭐

### 核心思路
使用 papermill 在 GitHub Actions 中执行 Notebook

### 实施步骤

#### Step 1: 参数化 Notebook
```python
# 在 Notebook 第一个 cell 添加参数
# Parameters
environment = "dev"  # Will be overridden by papermill
region = "us-east-1"
agent_name = "AWS_Support_Agent"
```

#### Step 2: GitHub Actions 执行
```yaml
# .github/workflows/deploy-with-notebook.yml
name: Deploy Infrastructure with Notebook

on:
  workflow_dispatch:
    inputs:
      environment:
        required: true
        type: choice
        options: [dev, staging, prod]

jobs:
  deploy-agent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install papermill jupyter
          pip install -r 04_create_knowledge_mcp_gateway_Agent/requirements.txt

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Execute Notebook
        run: |
          papermill \
            04_create_knowledge_mcp_gateway_Agent/deploy_QA_agent.ipynb \
            output_${{ github.event.inputs.environment }}.ipynb \
            -p environment "${{ github.event.inputs.environment }}" \
            -p region "us-east-1"

      - name: Upload executed notebook
        uses: actions/upload-artifact@v4
        with:
          name: executed-notebook
          path: output_*.ipynb
```

### 优点
- ✅ 保留 Notebook 工作流
- ✅ 可自动化
- ✅ 执行结果保存为 Notebook

### 缺点
- ⚠️ GitHub Actions 环境可能缺少 SageMaker 特定依赖
- ⚠️ Notebook 需要改造为参数化

---

## 方案 4: AWS Step Functions + Lambda ⭐⭐⭐⭐

### 核心思路
将部署逻辑封装到 Lambda，用 Step Functions 编排

### 架构
```
GitHub Push
  ↓
GitHub Actions (触发)
  ↓
AWS Step Functions (编排)
  ↓
┌────────────────────────────────────┐
│ Lambda 1: Deploy Knowledge Base    │
│ Lambda 2: Deploy Gateway           │
│ Lambda 3: Deploy Agent Runtime     │
└────────────────────────────────────┘
```

### 实施步骤

#### Step 1: 创建部署 Lambda
```python
# lambdas/deploy_knowledge_base.py
def lambda_handler(event, context):
    # 从 create_knowledge_base.ipynb 提取的逻辑
    kb_id = create_knowledge_base(
        name=event['kb_name'],
        region=event['region']
    )
    return {'kb_id': kb_id}
```

#### Step 2: 定义 Step Functions
```json
{
  "StartAt": "DeployKnowledgeBase",
  "States": {
    "DeployKnowledgeBase": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:deploy-kb",
      "Next": "DeployGateway"
    },
    "DeployGateway": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:deploy-gateway",
      "Next": "DeployAgent"
    },
    "DeployAgent": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:deploy-agent",
      "End": true
    }
  }
}
```

#### Step 3: GitHub Actions 触发
```yaml
- name: Trigger Step Functions
  run: |
    aws stepfunctions start-execution \
      --state-machine-arn ${{ secrets.STATE_MACHINE_ARN }} \
      --input '{"environment":"prod"}'
```

### 优点
- ✅ 完全自动化
- ✅ AWS 原生编排
- ✅ 可视化工作流
- ✅ 支持重试和错误处理

### 缺点
- ⚠️ 实施复杂度高
- ⚠️ 需要重写 Notebook 逻辑

---

## 🎯 我的推荐方案

### 对你的项目：**方案 1（分层自动化）**⭐⭐⭐⭐⭐

### 实施路径

#### 阶段 1: 立即可用（当前）
```
基础设施: SageMaker Notebook (手动)
  - Knowledge Base: 手动创建一次
  - Gateway: 手动创建一次
  - Agent Runtime: 手动首次部署

应用代码: GitHub Actions (自动)
  - Lambda 代码: 自动部署
  - Agent 代码: 热更新（不重建容器）
  - 配置: SSM Parameters 更新
```

#### 阶段 2: 逐步自动化（3-6 个月后）
```
提取核心 Notebook 逻辑 → Python 脚本
  ↓
GitHub Actions 调用脚本
  ↓
完全自动化基础设施部署
```

---

## 🛠️ 具体实施

### 修改现有 GitHub Actions

我需要更新现有的 workflows，明确区分：
1. **Lambda 部署**：完全自动化 ✅
2. **Agent 代码更新**：自动化（不重建容器）⚠️
3. **基础设施**：手动 + 文档化流程 📝

### 创建新 Workflow

#### 1. Agent 代码热更新
```yaml
# .github/workflows/update-agent-code.yml
name: Update Agent Code (Hot Update)

# 只更新代码，不重建 Docker 镜像
on:
  push:
    branches: [main]
    paths:
      - '04_create_knowledge_mcp_gateway_Agent/aws_support_agent.py'
      - '04_create_knowledge_mcp_gateway_Agent/streamable_http_sigv4.py'

jobs:
  update-code:
    runs-on: ubuntu-latest
    steps:
      - name: Update Agent Runtime code
        run: |
          # 使用 bedrock-agentcore CLI 更新代码
          bedrock-agentcore update-code \
            --agent-name AWS_Support_Agent \
            --code-path aws_support_agent.py
```

#### 2. 基础设施部署文档化
```markdown
# docs/INFRASTRUCTURE_DEPLOYMENT.md

## 基础设施部署（手动流程）

### 前置条件
- SageMaker Notebook Instance 已启动
- AWS Credentials 已配置

### 部署步骤

1. **创建知识库**
   ```bash
   # 在 SageMaker Notebook 中执行
   01_create_support_knowledegbase_rag/create_knowledge_base.ipynb
   ```

2. **创建 Gateway**
   ```bash
   03_create_agentcore_gateway/create_agentcore_gateway.ipynb
   ```

3. **首次部署 Agent**
   ```bash
   04_create_knowledge_mcp_gateway_Agent/deploy_QA_agent.ipynb
   ```

### 后续更新
- Lambda 代码: GitHub Actions 自动
- Agent 代码: GitHub Actions 自动（热更新）
- 配置: GitHub Actions 自动
```

---

## 📊 对比总结

| 方案 | 自动化程度 | 实施难度 | 推荐度 |
|------|-----------|---------|--------|
| **方案 1: 分层自动化** | ⭐⭐⭐ | ⭐ 简单 | ⭐⭐⭐⭐⭐ |
| 方案 2: Notebook → 脚本 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐ |
| 方案 3: Papermill | ⭐⭐⭐⭐ | ⭐⭐ 简单 | ⭐⭐⭐ |
| 方案 4: Step Functions | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ 复杂 | ⭐⭐⭐ |

---

## 🎯 下一步行动

### 立即执行
1. **接受分层架构**: 基础设施手动，应用代码自动
2. **更新 CI/CD Workflows**: 明确只自动化应用层
3. **创建基础设施部署文档**: 标准化手动流程

### 3 个月后
4. **评估 Notebook 使用频率**: 如果频繁变更，考虑方案 2
5. **提取核心逻辑**: 逐步将 Notebook 转为脚本

### 6 个月后
6. **完全自动化**: 如果团队成熟，实施方案 4

---

## 📞 需要我做什么？

我可以立即为你创建：
1. ✅ **更新的 GitHub Actions workflows**（明确分层）
2. ✅ **基础设施部署文档**（SageMaker Notebook 流程）
3. ✅ **Agent 代码热更新 workflow**
4. ✅ **混合 CI/CD 架构图**

需要我继续吗？
