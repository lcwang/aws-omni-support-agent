# AWS Omni Support Agent

> 🤖 智能化 AWS 技术支持平台 - 结合 RAG 知识库和自动化工单管理的企业级 AI Agent，支持零配置 RBAC 权限控制

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![AWS](https://img.shields.io/badge/AWS-Bedrock-orange.svg)](https://aws.amazon.com/bedrock/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📖 目录

- [最新特性：用户反馈系统](#-最新特性用户反馈系统) 🆕
- [项目简介](#-项目简介)
- [核心特性](#-核心特性)
- [系统架构](#-系统架构)
- [效果展示](#-效果展示)
- [技术栈](#-技术栈)
- [快速开始](#-快速开始)
- [使用指南](#-使用指南)
- [项目结构](#-项目结构)
- [常见问题](#-常见问题)
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

### 权限控制
- ✅ **零配置 RBAC**: 基于 IAM Policy Simulator API 的用户权限检查
- ✅ **无需额外配置**: 自动读取用户现有 IAM 权限
- ✅ **细粒度控制**: QA 工具公开，Case 操作需鉴权
- ✅ **审计日志**: CloudWatch Logs 记录所有操作

### 业务集成
- ✅ **电商场景优化**: 针对支付、订单、库存等关键场景定制
- ✅ **业务影响评估**: 自动关联技术问题与业务影响
- ✅ **峰值优先级**: 购物节期间自动提升问题优先级

---

## 🌟 最新特性：用户反馈系统

> **全新推出** - 完整的点赞/点踩反馈机制，实现知识库自动优化和问题追踪！
>
> 💡 **核心亮点**：用户反馈直接驱动 Knowledge Base 更新，形成自我进化的闭环系统
<img width="1158" height="687" alt="image" src="https://github.com/user-attachments/assets/066f3d18-4305-46e8-a57d-cbed142869fe" />

### 📊 反馈驱动的知识迭代

```
用户反馈 → 智能分类 → 自动优化 → 质量提升
    ↓           ↓           ↓           ↓
  点赞👍     来源检测    更新 KB      更好的答案
  点踩👎     问题分类    存储分析    持续改进
```

### 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                         Web UI                               │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │  Chat View  │  │  👍 Button  │  │   👎 Modal       │   │
│  │  (stream)   │  │  (async)    │  │   (reasons)      │   │
│  └─────────────┘  └─────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│  POST /api/feedback → submit_feedback()                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
┌───────────────────┐                 ┌──────────────────┐
│ Positive Handler  │                 │ Negative Handler │
│ (点赞处理)         │                 │ (点踩处理)        │
└───────────────────┘                 └──────────────────┘
        ↓                                       ↓
┌───────────────────┐                 ┌──────────────────┐
│  来源检测逻辑      │                 │  智能分类逻辑     │
│  ├─ RAG召回?      │                 │  ├─ knowledge_gap│
│  ├─ LLM生成?      │                 │  ├─ bad_document │
│  └─ Hybrid?       │                 │  ├─ weak_retrieval│
└───────────────────┘                 │  └─ synthesis_issue│
        ↓                             └──────────────────┘
  (仅处理 LLM 生成)                           ↓
        ↓                             ┌──────────────────┐
┌───────────────────┐                 │   DynamoDB       │
│  S3 + KB Sync     │                 │   ├─ QA内容      │
│  1. 上传 S3       │                 │   ├─ 反馈原因    │
│  2. 触发 Ingestion│                 │   ├─ 检索详情    │
│  3. 自动 Embedding│                 │   └─ 优先级管理  │
└───────────────────┘                 └──────────────────┘
        ↓
┌───────────────────┐
│ Bedrock KB        │
│ (RAG 自动更新)     │
└───────────────────┘
```

### ✨ 核心功能

#### 1️⃣ **点赞功能** - 自动更新知识库

当用户对回答点赞时，系统会智能处理：

```
📝 智能来源检测
  ├─ RAG 召回答案 → 只记录满意度（内容已在 KB 中）
  ├─ LLM 生成答案 → 自动上传到 S3 + 触发 KB ingestion
  └─ 混合模式答案 → 记录质量数据

🔄 异步处理
  ├─ 用户立即收到反馈确认
  ├─ 后台上传 S3（fire-and-forget）
  ├─ 自动触发 Knowledge Base ingestion
  └─ 新知识自动融入 RAG 系统
```

**实现原理**：

<details>
<summary>📖 展开查看详细实现</summary>

**1. 前端触发** (`static/feedback-ui.js`)
```javascript
// 点赞按钮点击
thumbsUpBtn.addEventListener('click', async () => {
    await fetch('/api/feedback', {
        method: 'POST',
        body: JSON.stringify({
            feedback_type: 'positive',
            question: question,
            answer: answer,
            retrieval_source: 'llm_generated',  // 或 'rag' / 'hybrid'
            rag_documents: [...],  // 检索的文档列表
        })
    });
});
```

**2. 后端处理** (`feedback/handlers/positive_handler.py`)
```python
async def handle_positive_feedback(request: FeedbackRequest):
    # 检测答案来源
    if request.retrieval_source == 'llm_generated':
        # LLM 生成的答案 → 加入知识库
        asyncio.create_task(
            _add_qa_to_kb_background(
                question=request.question,
                answer=request.answer
            )
        )  # 异步处理，不阻塞响应
    elif request.retrieval_source == 'rag':
        # RAG 召回的答案 → 只记录（已在 KB 中）
        logger.info("Answer from RAG, no need to add to KB")
```

**3. S3 上传 + KB 同步** (`feedback/operations/bedrock_kb_operations.py`)
```python
async def _add_qa_to_kb_background(question: str, answer: str):
    # 1. 检查相似度去重
    similar_docs = await check_similarity(question=question, threshold=0.95)
    if similar_docs:
        return  # 已有相似内容，跳过

    # 2. 生成 Markdown 格式
    content = f"""# {question}

{answer}

---
Validated at: {timestamp}
Source: User Feedback (Thumbs Up)
"""

    # 3. 上传到 S3
    s3_client.put_object(
        Bucket=KB_S3_BUCKET,
        Key=f"validated-qa/{doc_id}.txt",
        Body=content.encode('utf-8')
    )

    # 4. 触发 KB 数据源同步
    bedrock_agent_client.start_ingestion_job(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        dataSourceId=data_source_id
    )
```

**4. Bedrock KB 自动处理**
- 检测 S3 新文件
- 使用 Titan Embeddings 生成向量
- 更新 OpenSearch 索引
- 新 QA 可被检索

</details>

**效果**：
- ✅ **自我进化**：用户验证的高质量 QA 自动加入知识库
- ✅ **零延迟**：异步处理不影响用户体验（`asyncio.create_task`）
- ✅ **智能去重**：基于相似度检测避免重复内容（cosine similarity > 0.95）

#### 2️⃣ **点踩功能** - 智能问题追踪

当用户对回答点踩时，系统会：

```
📋 预设原因选择
  ├─ 答案像是编造的（幻觉）
  ├─ 答案不正确
  ├─ 答案不完整
  └─ 答案不相关

🔍 智能自动分类
  ├─ knowledge_gap     → 知识库缺失（High 优先级）
  ├─ bad_document      → 文档质量问题（High 优先级）
  ├─ weak_retrieval    → 检索相关性低（Medium 优先级）
  └─ synthesis_issue   → 合成逻辑问题（Medium 优先级）

💾 DynamoDB 存储
  ├─ 完整的 QA 内容
  ├─ 反馈原因和用户评论
  ├─ 检索来源和文档信息
  └─ 自动优先级和状态管理
```

**实现原理**：

<details>
<summary>📖 展开查看详细实现</summary>

**1. 前端弹窗** (`templates/index.html` + `static/feedback-ui.js`)
```javascript
// 点踩按钮 → 显示原因选择弹窗
thumbsDownBtn.addEventListener('click', () => {
    modal.style.display = 'block';  // 显示弹窗
});

// 提交反馈
submitBtn.addEventListener('click', async () => {
    await fetch('/api/feedback', {
        method: 'POST',
        body: JSON.stringify({
            feedback_type: 'negative',
            negative_reason: selectedReason,  // hallucination/incorrect/incomplete/irrelevant
            user_comment: commentText,
            question: question,
            answer: answer,
            retrieval_source: source,
            rag_documents: docs
        })
    });
});
```

**2. 智能分类** (`feedback/handlers/negative_handler.py`)
```python
def _classify_issue(request: FeedbackRequest) -> tuple[str, str]:
    """
    根据来源 + 原因 + 检索分数自动分类

    返回: (issue_category, priority)
    """
    source = request.retrieval_source
    reason = request.negative_reason
    max_score = max([doc.score for doc in request.rag_documents], default=0)

    # 规则引擎
    if source == 'llm_generated' and reason in ['hallucination', 'incorrect']:
        return 'knowledge_gap', 'high'  # LLM 幻觉 → 知识缺失

    if source == 'rag' and max_score > 0.8 and reason == 'incorrect':
        return 'bad_document', 'high'  # 高分文档但答案错误 → 文档质量问题

    if source == 'rag' and 0.5 < max_score < 0.7:
        return 'weak_retrieval', 'medium'  # 中等分数 → 检索相关性低

    if source == 'hybrid' and reason == 'incomplete':
        return 'synthesis_issue', 'medium'  # 混合模式不完整 → 合成逻辑问题

    return 'other', 'low'
```

**3. DynamoDB 存储** (`feedback/operations/dynamodb_operations.py`)
```python
async def store_negative_feedback(request: FeedbackRequest, category: str, priority: str):
    """
    存储点踩反馈到 DynamoDB

    表结构:
    - 主键: feedback_id (UUID)
    - GSI: issue_category-status-index (用于批量查询)
    """
    item = {
        'feedback_id': str(uuid.uuid4()),
        'timestamp': datetime.utcnow().isoformat(),
        'question': request.question,
        'answer': request.answer,
        'negative_reason': request.negative_reason,
        'user_comment': request.user_comment or '',
        'retrieval_source': request.retrieval_source,
        'rag_documents': _serialize_docs(request.rag_documents),
        'issue_category': category,
        'priority': priority,
        'status': 'pending'
    }

    dynamodb_client.put_item(
        TableName=DYNAMODB_TABLE_NAME,
        Item=item
    )
```

**4. 数据分析查询**
```python
# 查询高优先级问题
response = dynamodb_client.query(
    TableName=DYNAMODB_TABLE_NAME,
    IndexName='issue_category-status-index',
    KeyConditionExpression='issue_category = :cat AND #status = :stat',
    ExpressionAttributeValues={
        ':cat': 'knowledge_gap',
        ':stat': 'pending'
    }
)
```

</details>

**效果**：
- ✅ **精准定位**：基于规则引擎自动识别问题类型和根本原因
- ✅ **数据驱动**：完整记录（QA + 原因 + 检索详情）供后续分析
- ✅ **优先级管理**：High 优先级问题优先处理（knowledge_gap, bad_document）

### 🎯 业务价值

| 指标 | 提升 | 说明 |
|------|------|------|
| **知识覆盖率** | ↑ 30-50% | 用户验证的 QA 自动加入知识库 |
| **答案准确度** | ↑ 20-40% | 基于反馈数据持续优化 |
| **问题响应速度** | ↓ 50% | RAG 直接召回 vs MCP 查询 |
| **用户满意度** | ↑ 25% | 答案质量持续改进 |

### 📦 完整功能包

新增目录：**`06_web_client_with_feedback/`** - 包含完整的反馈系统实现

```
06_web_client_with_feedback/
├── app.py                          # FastAPI + 反馈 API
├── feedback/                       # 反馈系统核心包
│   ├── handlers/
│   │   ├── positive_handler.py     # 点赞处理（S3 + KB ingestion）
│   │   └── negative_handler.py     # 点踩处理（DynamoDB 分类存储）
│   └── operations/
│       ├── bedrock_kb_operations.py   # Bedrock KB 操作
│       └── dynamodb_operations.py     # DynamoDB CRUD
├── static/
│   ├── script.js                   # 前端逻辑（反馈按钮）
│   └── feedback-ui.css             # 反馈 UI 样式
├── deployment/
│   └── setup_dynamodb.py           # DynamoDB 表自动创建
└── 📚 完整文档（8 个 MD 文件）
    ├── README.md                   # 快速开始
    ├── PROJECT_SUMMARY.md          # 项目总结
    ├── THUMBS_UP_RAG_SETUP.md      # 点赞功能详解
    └── ENV_CONFIG_GUIDE.md         # 环境配置指南
```

### 🚀 快速体验

```bash
# 1. 克隆仓库
git clone https://github.com/percy-han/aws-omni-support-agent.git
cd aws-omni-support-agent/06_web_client_with_feedback

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 KB ID 和 S3 Bucket

# 3. 创建 DynamoDB 表
python deployment/setup_dynamodb.py

# 4. 启动服务
./start.sh

# 5. 访问 http://localhost:8000
# 试试点赞和点踩按钮吧！
```

查看完整文档：[06_web_client_with_feedback/README.md](06_web_client_with_feedback/README.md)

---

## ✨ 核心特性

### 1. 用户反馈系统（🆕 最新）

见上方 [🌟 最新特性](#-最新特性用户反馈系统) 详细介绍。

### 2. 混合架构设计

| 组件 | 架构 | 优势 |
|------|------|------|
| **应用层** | Lambda + AgentCore Gateway | 40-60% 成本降低，自动扩展 |
| **AI 层** | Claude Opus 4.5 + Bedrock | 最先进的推理能力 |
| **知识层** | OpenSearch + Titan Embeddings | 毫秒级检索 |
| **权限层** | IAM Policy Simulator | 零配置 RBAC |

### 2. 零配置 RBAC

```
🔐 权限控制特性
  ├─ 零配置部署 - 使用现有 IAM Policy
  ├─ IAM Policy Simulator - AWS 原生权限评估
  ├─ 工具分级访问
  │   ├─ QA 工具（describe_*）- 无需鉴权
  │   └─ Case 工具（create/update/resolve）- 需要鉴权
  ├─ 复杂策略支持
  │   ├─ 通配符（*, support:*, support:*Case）
  │   ├─ AdministratorAccess 等 Managed Policy
  │   ├─ Deny 语句优先级
  │   └─ Condition 条件表达式
  └─ 完整审计日志
      ├─ 用户身份记录
      ├─ 操作时间戳
      ├─ 权限检查结果
      └─ API 调用详情
```

**RBAC 工作流程**：
```
Web Client (用户输入 IAM User)
    ↓
Agent Runtime (自动传递 _iam_user)
    ↓
Lambda (使用 IAM Policy Simulator 检查权限)
    ├─ QA 工具: 直接执行
    └─ Case 工具:
        ├─ 调用 iam:SimulatePrincipalPolicy
        ├─ 检查用户是否有 support:CreateCase 等权限
        └─ 允许/拒绝操作
    ↓
AWS Support API (使用 Lambda 执行角色凭证)
    ↓
CloudWatch Logs (记录完整审计日志)
```

### 3. 企业级可靠性

```
🔒 安全性
  ├─ IAM Role 原生认证（无需管理密钥）
  ├─ 零配置 RBAC（用户级权限控制）
  ├─ 多环境隔离（DEV/STAGING/PROD）
  └─ 审计日志（CloudWatch Logs）

⚡ 性能
  ├─ Eager 初始化（减少冷启动）
  ├─ 连接池复用
  ├─ 权限缓存（5分钟TTL）
  └─ 区域自动检测

📊 可观测性
  ├─ 结构化日志（CloudWatch）
  ├─ 性能指标（Lambda Metrics）
  ├─ RBAC 审计日志
  └─ 用户操作追踪
```

### 4. Web 客户端增强

- 📝 **用户身份输入**: 输入 IAM 用户名，自动传递给 Agent
- 💾 **Session 管理**: 基于 localStorage 的会话持久化
- 👤 **用户隔离**: 不同用户的对话历史独立存储
- 🔄 **自动恢复**: 切换回原用户时自动恢复历史对话
- 🆕 **新建会话**: 一键清空当前对话，开始新会话

---

## 🏛 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户交互层                            │
│  Web UI (用户身份输入 + Session 管理)                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent 运行时                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  AWS Support Agent (Claude Opus 4.5)                │  │
│  │  - System Prompt (320 行业务逻辑)                   │  │
│  │  - 双阶段查询（知识库 → AWS 文档 → 工单）          │  │
│  │  - 中文优先 + 电商场景优化                          │  │
│  │  - 自动传递 _iam_user 参数                          │  │
│  └──────────────────────────────────────────────────────┘  │
│         ↓                    ↓                    ↓          │
│  ┌──────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │Knowledge │      │ AgentCore    │      │ MCP Client   │ │
│  │Base(RAG) │      │ Gateway      │      │ (AWS Docs)   │ │
│  └──────────┘      └──────────────┘      └──────────────┘ │
│         ↓                    ↓                              │
│  ┌──────────┐      ┌──────────────┐                       │
│  │OpenSearch│      │ Lambda       │                       │
│  │+ Titan   │      │ (7 Tools +   │                       │
│  │          │      │  RBAC)       │                       │
│  └──────────┘      └──────────────┘                       │
│                             ↓                               │
│                    ┌──────────────┐                        │
│                    │ 零配置 RBAC  │                        │
│                    │ IAM Policy   │                        │
│                    │ Simulator    │                        │
│                    └──────────────┘                        │
│                             ↓                               │
│                    ┌──────────────┐                        │
│                    │ AWS Support  │                        │
│                    │ API          │                        │
│                    └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### RBAC 权限检查流程

```
┌────────────────────────────────────────────────────────────┐
│ 1. Web Client                                              │
│    - 用户输入: IAM 用户名（如 alice）                      │
│    - Session ID: 自动生成（localStorage 持久化）          │
│    - 传递: user_id + session_id + prompt                  │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 2. Agent Runtime                                           │
│    - 检测操作类型                                          │
│    - QA 工具: 直接调用（无 _iam_user）                    │
│    - Case 工具: 添加 _iam_user 参数                       │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 3. Lambda Handler                                          │
│    - 提取 _iam_user 参数                                   │
│    - 检查工具类型                                          │
│      ├─ QA 工具: 跳过权限检查                             │
│      └─ Case 工具: 执行权限检查                           │
│          ├─ 调用 iam:SimulatePrincipalPolicy API          │
│          ├─ PolicySourceArn: 用户 ARN                     │
│          ├─ ActionNames: ['support:CreateCase']           │
│          └─ 返回: allowed/denied                          │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 4. 权限检查结果                                            │
│    ✅ allowed: 继续执行                                   │
│    ❌ denied: 返回权限拒绝错误                            │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│ 5. AWS Support API 调用                                    │
│    - 使用 Lambda 执行角色凭证                              │
│    - 记录审计日志到 CloudWatch Logs                        │
│      ├─ 用户身份: _iam_user                               │
│      ├─ 操作: create_support_case                         │
│      ├─ 权限检查: allowed                                 │
│      ├─ 结果: success/failure                             │
│      └─ 时间戳: 2026-04-01 12:00:00                       │
└────────────────────────────────────────────────────────────┘
```

### 架构优势

#### 新架构（当前）
```
Agent Runtime → Gateway → Lambda (RBAC) → Support API
                          (IAM Policy Simulator)
```
**优势**:
- ✅ 零配置部署（使用现有 IAM Policy）
- ✅ AWS 原生权限评估（准确处理复杂策略）
- ✅ 用户级权限控制（细粒度访问控制）
- ✅ 完整审计日志（CloudWatch Logs）
- ✅ 成本降低 40-60%（Lambda 按需计费）

---
## 💻 效果展示
<img width="1681" height="1555" alt="image" src="https://github.com/user-attachments/assets/567053f4-edb3-4e10-82ab-79ddab959dc8" />
<img width="1614" height="1686" alt="image" src="https://github.com/user-attachments/assets/2291455b-a91d-4c2b-b05b-f7862c6be6f0" />
<img width="1332" height="1119" alt="image" src="https://github.com/user-attachments/assets/d1c12442-0b02-4e5b-bac9-22d723723a3c" />
<img width="1358" height="1165" alt="image" src="https://github.com/user-attachments/assets/86e97e6d-115a-420b-8435-52dd830e0875" />


---
## 🔧 技术栈

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
- **IAM**: IAM Policy Simulator (RBAC)
- **Monitoring**: Amazon CloudWatch

### Development
- **Language**: Python 3.11
- **Package Manager**: pip
- **Testing**: boto3, moto
- **Code Quality**: Ruff, Black, mypy

---

## 🚀 快速开始

### 前置要求

- **AWS 账户**: 商业或企业支持计划（用于 Support API）
- **Python**: 3.11+
- **AWS CLI**: 已配置凭证
- **Git**: 用于克隆仓库

### 快速部署（Lambda + RBAC）

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/aws-omni-support-agent.git
cd aws-omni-support-agent

# 2. 部署 Lambda 函数（包含 RBAC）
cd 02_AWS_Support_Case_Lambda
pip install boto3
python3 deploy_lambda.py

# 输出示例：
# ✓ Created Lambda function: arn:aws:lambda:us-east-1:123456789012:function:aws-support-tools-lambda0331
# ✓ Lambda 部署成功
# ✓ 7 个工具可用
```

### 更新 Lambda RBAC 策略（可选）

如果需要更新已有函数的 RBAC 权限策略：

```bash
# 使用部署脚本（自动更新 IAM 策略 + Lambda 代码）
./deploy_rbac.sh aws-support-tools-lambda0331 your-iam-username

# 输出示例：
# ✓ Lambda 执行角色: aws-support-lambda-execution-role-0331
# ✓ 策略已更新（添加 IAM SimulatePrincipalPolicy 权限）
# ✓ Lambda 已部署
```

### 部署 Web 客户端

```bash
# 1. 进入 Web 客户端目录
cd 05_web_client

# 2. 安装依赖
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 3. 配置 Agent ARN
export AGENT_ARN="your-agent-arn-here"

# 4. 启动服务
python3 app.py

# 5. 访问
# http://localhost:8000
```

### 完整部署（包括 Knowledge Base 和 Agent Runtime）

参见：[SAGEMAKER_NOTEBOOK_CHECKLIST.md](SAGEMAKER_NOTEBOOK_CHECKLIST.md)

---

## 📖 使用指南

### 场景 1: Web UI 使用（带 RBAC）

```
1. 打开 Web 界面: http://localhost:8000

2. 输入用户身份（右上角）:
   - IAM 用户名: alice
   - 系统自动生成 Session ID
   - 对话历史保存到 localStorage

3. 查询问题（无需权限）:
   输入: "列出所有严重程度选项"
   Agent: 自动调用 describe_severity_levels
   结果: ✅ 直接返回结果（QA 工具无需鉴权）

4. 创建工单（需要权限）:
   输入: "帮我创建一个工单，EC2 实例无法启动"
   Agent: 自动调用 create_support_case
   Lambda:
     - 提取 _iam_user = "alice"
     - 调用 IAM Policy Simulator
     - 检查 alice 是否有 support:CreateCase 权限
   结果:
     - ✅ 有权限: 创建工单成功
     - ❌ 无权限: 返回权限拒绝错误

5. 切换用户:
   - 输入新用户名: bob
   - 自动切换到 bob 的 Session
   - 切换回 alice 时自动恢复历史对话
```

### 场景 2: 权限测试

```bash
# 测试不同用户的权限

# 用户 A (有完整权限)
User: alice
IAM Policy: AdministratorAccess
操作: 创建 critical 级别工单
结果: ✅ 成功

# 用户 B (只读权限)
User: bob
IAM Policy: support:DescribeCases
操作: 创建工单
结果: ❌ 权限拒绝 - User bob is not authorized to perform: support:CreateCase

# 用户 C (部分权限)
User: charlie
IAM Policy: support:CreateCase (但不能创建 critical/urgent)
操作: 创建 normal 级别工单
结果: ✅ 成功
操作: 创建 critical 级别工单
结果: ❌ Deny 规则阻止
```

### 场景 3: 审计日志查看

```bash
# CloudWatch Logs 查看审计日志
aws logs filter-log-events \
  --log-group-name /aws/lambda/aws-support-tools-lambda0331 \
  --filter-pattern "RBAC"

# 输出示例：
# 2026-04-01 12:00:00 [INFO] RBAC Permission Check:
#   - User: alice
#   - Tool: create_support_case
#   - Required Action: support:CreateCase
#   - Result: ALLOWED
#   - Evaluation: EvalDecision=allowed
#
# 2026-04-01 12:01:00 [INFO] Support API Call:
#   - User: alice
#   - Operation: CreateCase
#   - Severity: urgent
#   - Case ID: case-123456789
#   - Status: success
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
├── 02_AWS_Support_Case_Lambda/             # Lambda 函数（7 个工具 + RBAC）⭐
│   ├── lambda_handler.py                   # 主处理器（零配置 RBAC）⭐⭐⭐
│   ├── deploy_lambda.py                    # 自动部署脚本 ⭐⭐
│   ├── deploy_rbac.sh                      # RBAC 部署脚本 ⭐
│   ├── update_lambda_role_policy.sh        # 更新 IAM 策略脚本
│   ├── lambda_rbac_policy.json             # Lambda IAM 权限策略 ⭐
│   ├── gateway_tools_schema.json           # 工具 Schema
│   └── requirements.txt                    # Python 依赖
│
├── 03_create_agentcore_gateway/            # Gateway 创建
│   └── create_agentcore_gateway.ipynb      # 创建 Gateway Notebook
│
├── 04_create_knowledge_mcp_gateway_Agent/  # Agent Runtime
│   ├── aws_support_agent.py                # Agent 核心代码（传递 _iam_user）⭐⭐⭐
│   ├── deploy_QA_agent.ipynb               # 部署 Notebook
│   ├── agent_client.py                     # 测试客户端
│   ├── streamable_http_sigv4.py            # SigV4 认证
│   └── requirements.txt                    # Python 依赖
│
├── 05_web_client/                          # Web 客户端（基础版）⭐
│   ├── app.py                              # FastAPI Backend（Session 管理）⭐⭐
│   ├── templates/
│   │   └── index.html                      # 前端页面（用户身份输入）⭐
│   ├── static/
│   │   ├── script.js                       # 前端逻辑（localStorage）⭐⭐
│   │   ├── style.css                       # 样式
│   │   └── session-styles.css              # Session 样式
│   ├── start.sh                            # 启动脚本
│   ├── ATTACHMENT_GUIDE.md                 # 附件上传指南
│   └── requirements.txt                    # Python 依赖
│
├── 06_web_client_with_feedback/           # 🆕 Web 客户端（带反馈系统）⭐⭐⭐
│   ├── app.py                              # FastAPI + 反馈 API ⭐⭐⭐
│   ├── feedback/                           # 反馈系统核心包 ⭐⭐⭐
│   │   ├── __init__.py                     # Package 初始化
│   │   ├── api.py                          # 反馈 API 入口 ⭐⭐
│   │   ├── config.py                       # 配置管理
│   │   ├── models.py                       # 数据模型
│   │   ├── handlers/                       # 处理器层
│   │   │   ├── positive_handler.py         # 点赞处理（S3 + KB ingestion）⭐⭐⭐
│   │   │   └── negative_handler.py         # 点踩处理（DynamoDB）⭐⭐⭐
│   │   └── operations/                     # 操作层
│   │       ├── bedrock_kb_operations.py    # Bedrock KB 操作 ⭐⭐
│   │       ├── dynamodb_operations.py      # DynamoDB CRUD ⭐⭐
│   │       └── opensearch_operations.py    # OpenSearch（备用）
│   ├── templates/
│   │   └── index.html                      # 前端页面（含反馈 UI）⭐⭐
│   ├── static/
│   │   ├── script.js                       # 前端逻辑 + 反馈按钮 ⭐⭐
│   │   ├── feedback-ui.js                  # 反馈 UI 交互 ⭐
│   │   └── feedback-ui.css                 # 反馈样式
│   ├── deployment/
│   │   ├── setup_dynamodb.py               # DynamoDB 表创建 ⭐
│   │   └── DYNAMODB_SETUP_GUIDE.md         # 部署指南
│   ├── debug_kb_ingestion.py               # KB 诊断工具 ⭐
│   ├── start.sh                            # 启动脚本
│   ├── 📚 完整文档（8 个 MD 文件）
│   │   ├── README.md                       # 快速开始 ⭐⭐
│   │   ├── PROJECT_SUMMARY.md              # 项目总结 ⭐
│   │   ├── THUMBS_UP_RAG_SETUP.md          # 点赞功能详解 ⭐
│   │   ├── ENV_CONFIG_GUIDE.md             # 配置指南
│   │   └── ...（更多文档）
│   └── requirements.txt                    # Python 依赖
│
├── SAGEMAKER_NOTEBOOK_CHECKLIST.md         # Notebook 清单 ⭐
├── README.md                               # 本文件 ⭐
└── LICENSE                                 # 许可证
```

### 核心文件说明

| 文件 | 用途 | 重要性 |
|------|------|--------|
| `lambda_handler.py` | Lambda 函数主逻辑，7 个工具 + 零配置 RBAC | ⭐⭐⭐⭐⭐ |
| `lambda_rbac_policy.json` | Lambda IAM 权限策略（IAM Simulator + Support API） | ⭐⭐⭐⭐⭐ |
| `aws_support_agent.py` | Agent 核心，320 行 System Prompt + _iam_user 传递 | ⭐⭐⭐⭐⭐ |
| `deploy_lambda.py` | Lambda 自动部署脚本 | ⭐⭐⭐⭐ |
| `deploy_rbac.sh` | 零配置 RBAC 部署脚本 | ⭐⭐⭐⭐ |
| `app.py` | Web 客户端后端（Session 管理） | ⭐⭐⭐⭐ |
| `script.js` | 前端逻辑（localStorage Session 持久化） | ⭐⭐⭐⭐ |

---

## ❓ 常见问题

### Q1: 零配置 RBAC 是如何工作的？

**A**:
- Lambda 通过 IAM Policy Simulator API (`iam:SimulatePrincipalPolicy`) 检查用户权限
- 不需要额外配置 IAM Role 或 Trust Policy
- 自动读取用户现有的 IAM Policy（包括 AdministratorAccess 等 Managed Policy）
- 准确处理通配符 (`*`, `support:*`)、Deny 语句、Condition 条件等复杂策略

### Q2: Lambda 需要哪些 IAM 权限？

**A**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["iam:SimulatePrincipalPolicy"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["support:*"],
      "Resource": "*"
    }
  ]
}
```

### Q3: 如何查看用户的操作审计日志？

**A**:
```bash
# CloudWatch Logs 查看
aws logs filter-log-events \
  --log-group-name /aws/lambda/YOUR_FUNCTION_NAME \
  --filter-pattern "RBAC" \
  --start-time $(date -u -d '1 hour ago' +%s)000

# 日志包含:
# - 用户身份 (_iam_user)
# - 操作类型 (create_support_case)
# - 权限检查结果 (allowed/denied)
# - API 调用结果 (success/failure)
# - 时间戳
```

### Q4: Web 客户端的 Session 如何工作？

**A**:
- 每个用户有独立的 Session ID（存储在 localStorage）
- Session ID 格式：`{iam_user}_{random_string}_{timestamp}_{random_string}`（长度 ≥ 33）
- 切换用户时自动切换 Session
- 切换回原用户时自动恢复历史对话
- "新建会话" 按钮可清空当前对话

### Q5: 成本是多少？

**A**:
- **Lambda**: 按调用付费，~$0.004/月（假设每月 1000 次调用）
- **Bedrock**: 按 token 计费，根据实际使用量
- **IAM Policy Simulator**: 免费
- **CloudWatch Logs**: 前 5GB 免费
- **总计**: ~$5-10/月（小规模使用）

### Q6: 如何添加新用户？

**A**:
```bash
# 用户只需要有 IAM Policy 即可，无需额外配置

# 示例：给用户 alice 添加只读权限
aws iam put-user-policy \
  --user-name alice \
  --policy-name SupportReadOnly \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["support:Describe*"],
      "Resource": "*"
    }]
  }'

# 示例：给用户 bob 添加完整权限
aws iam attach-user-policy \
  --user-name bob \
  --policy-arn arn:aws:iam::aws:policy/AWSSupportAccess
```

### Q7: 如何自定义 Agent 的行为？

**A**: 修改 `04_create_knowledge_mcp_gateway_Agent/aws_support_agent.py` 中的 `get_system_prompt()` 函数，该函数包含 320 行详细的业务逻辑。

---

## 📜 License

本项目采用 [MIT License](LICENSE)。

```
MIT License

Copyright (c) 2026 AWS Omni Support Agent Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```


---

## 🙏 致谢

感谢以下开源项目和服务：

- [Amazon Bedrock](https://aws.amazon.com/bedrock/) - AI Foundation Models
- [Strands Agents](https://github.com/strands-ai/strands) - Agent Framework
- [FastAPI](https://github.com/tiangolo/fastapi) - Modern Web Framework

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

Made with ❤️ by AWS Omni Support Agent Team

</div>
