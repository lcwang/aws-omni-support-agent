# 项目总结：Web Client with Feedback System

## 📝 需求概述

为 AWS Support Agent 添加完整的用户反馈系统，包括：
- ✅ **点赞功能**：用户验证的高质量 QA 自动加入 Knowledge Base
- ✅ **点踩功能**：收集问题反馈，存储到 DynamoDB 供后续分析
- ✅ **Web 客户端**：提供友好的交互界面

## 🏗️ 架构设计

```
用户 → Web UI → FastAPI Backend → Feedback System → AWS Services
                                      ├─ 点赞 → S3 + Bedrock KB Ingestion
                                      └─ 点踩 → DynamoDB
```

## 📦 核心模块

### 1. **Feedback Package** (`feedback/`)

完整的反馈处理系统，采用模块化设计：

```
feedback/
├── api.py                    # 统一 API 入口
├── config.py                 # 环境变量配置
├── models.py                 # Pydantic 数据模型
├── handlers/                 # 反馈处理器
│   ├── positive_handler.py   # 点赞：上传 S3 + 触发 KB ingestion
│   └── negative_handler.py   # 点踩：分类 + 存储 DynamoDB
└── operations/               # AWS 服务操作
    ├── bedrock_kb_operations.py   # Bedrock KB（S3 data source + ingestion）
    ├── dynamodb_operations.py     # DynamoDB CRUD
    └── opensearch_operations.py   # OpenSearch（备用方案）
```

**设计亮点**：
- **来源检测**：识别答案来自 RAG / LLM / Hybrid
- **智能处理**：RAG 答案只记录，LLM 答案上传到 KB
- **异步上传**：使用 `asyncio.create_task()` 不阻塞用户响应
- **去重机制**：基于相似度检测避免重复内容

### 2. **Web Client** (`app.py`, `static/`, `templates/`)

**前端功能**：
- 流式输出（Server-Sent Events）
- Session 管理（localStorage 持久化）
- 附件上传（支持多文件，最大 25MB）
- 点赞/点踩按钮（动态创建）
- 点踩弹窗（预设原因 + 自由输入）

**后端 API**：
- `POST /chat` - 对话接口（调用 Agent）
- `POST /api/feedback` - 反馈提交
- `GET /api/feedback/health` - 健康检查
- `GET /api/feedback/stats` - 统计数据

### 3. **部署工具** (`deployment/`)

- `setup_dynamodb.py` - 自动创建 DynamoDB 表（包含 GSI）
- `DYNAMODB_SETUP_GUIDE.md` - 完整部署指南

### 4. **诊断工具**

- `debug_kb_ingestion.py` - KB ingestion 全流程诊断
  - 检查环境配置
  - 验证 S3 文件
  - 查看 Ingestion Job 状态
  - 测试 KB 检索

## 🔑 关键技术点

### 1. 环境变量配置

使用 `.env` 文件管理配置，支持：
- AWS 区域和账户
- Agent ARN
- Knowledge Base ID 和 S3 Bucket
- DynamoDB 表名

**安全实践**：
- ✅ `.env` 在 `.gitignore` 中
- ✅ 提供 `.env.example` 模板
- ✅ `start.sh` 自动加载环境变量

### 2. 点赞更新 RAG 流程

```python
点赞 → positive_handler
     ↓
  判断来源
     ├─ RAG 召回 → 只记录（内容已在 KB）
     ├─ LLM 生成 → 上传 S3 + 触发 ingestion
     └─ Hybrid   → 只记录（避免重复）
```

**异步处理**：
```python
async def _handle_llm_thumbs_up(...):
    # 启动后台任务（fire-and-forget）
    asyncio.create_task(_add_qa_to_kb_background(...))
    # 立即返回
    return {"action": "add_to_rag_async"}
```

### 3. 点踩分类逻辑

根据 `retrieval_source` + `negative_reason` 自动分类：

| 分类 | 条件 | 优先级 |
|------|------|--------|
| `knowledge_gap` | LLM 生成 + 幻觉/错误 | High |
| `bad_document` | RAG 召回 + 高分 + 错误 | High |
| `weak_retrieval` | RAG 召回 + 中等分数 | Medium |
| `synthesis_issue` | Hybrid + 不完整 | Medium |

### 4. DynamoDB 数据模型

**表结构**：
- **主键**：`feedback_id` (UUID)
- **GSI**：`issue_category-status-index`（用于批量查询）
- **关键字段**：
  - `question`, `answer` - QA 内容
  - `negative_reason`, `user_comment` - 反馈原因
  - `retrieval_source`, `rag_documents` - 来源信息
  - `issue_category`, `priority`, `status` - 分类和状态

**特殊处理**：
- Float → Decimal 转换（DynamoDB 不支持 float）
- 空字符串 → "N/A"（DynamoDB 不支持空字符串）

## 📊 与原版本对比

| 功能 | 05_web_client | 06_web_client_with_feedback |
|------|---------------|----------------------------|
| 基础对话 | ✅ | ✅ |
| 流式输出 | ✅ | ✅ |
| Session 管理 | ✅ | ✅ |
| 附件上传 | ✅ | ✅ |
| **点赞功能** | ❌ | ✅ 自动更新 KB |
| **点踩功能** | ❌ | ✅ 存储到 DynamoDB |
| **反馈 UI** | ❌ | ✅ 按钮 + 弹窗 |
| **来源追踪** | ❌ | ✅ RAG/LLM/Hybrid |
| **环境变量配置** | ❌ | ✅ .env 管理 |
| **诊断工具** | ❌ | ✅ KB ingestion 诊断 |

## 🚀 快速开始

### 1. 环境准备

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置（填入实际值）
vim .env
```

### 2. 创建 DynamoDB 表

```bash
python deployment/setup_dynamodb.py
```

### 3. 启动服务

```bash
chmod +x start.sh
./start.sh
```

访问：http://localhost:8000

## 📚 文档索引

| 文档 | 用途 |
|------|------|
| `README.md` | 项目主文档 |
| `ENV_CONFIG_GUIDE.md` | 环境变量完整配置指南 |
| `THUMBS_UP_RAG_SETUP.md` | 点赞更新 RAG 功能详细说明 |
| `deployment/DYNAMODB_SETUP_GUIDE.md` | DynamoDB 表创建指南 |
| `COMPARISON.md` | Feedback 实现方案对比 |
| `RETRIEVAL_TRACKING_GUIDE.md` | 检索结果追踪方案 |

## 🔧 故障排查

### 问题 1：点赞后没有生成 S3 文件

**诊断**：
```bash
python debug_kb_ingestion.py
```

**检查**：
- 环境变量 `KNOWLEDGE_BASE_ID` 和 `KB_S3_BUCKET` 是否配置
- IAM 权限是否包含 `s3:PutObject` 和 `bedrock:StartIngestionJob`

### 问题 2：点踩提交失败

**常见原因**：
- DynamoDB 表未创建
- 数据包含 float 类型（需要转 Decimal）
- IAM 权限缺少 `dynamodb:PutItem`

### 问题 3：浏览器缓存问题

**解决**：
```
Cmd + Shift + R (Mac)
Ctrl + Shift + R (Windows)
```

或使用隐私/无痕模式。

## 📈 未来优化

### 短期
- [ ] 增加反馈统计面板
- [ ] 支持批量导出反馈数据
- [ ] 优化跨语言检索（英文→中文）

### 中期
- [ ] 添加管理后台（审核反馈）
- [ ] 实现 A/B 测试框架
- [ ] 集成 CloudWatch 监控

### 长期
- [ ] 使用 LLM 自动分类问题
- [ ] 基于反馈数据训练优化模型
- [ ] 多租户支持

## 🎯 核心价值

1. **闭环改进**：用户反馈 → Knowledge Base 自动更新 → 答案质量提升
2. **数据驱动**：所有反馈存储，支持后续分析和优化
3. **用户友好**：简洁的 UI，不打断对话流程
4. **运维友好**：完整的诊断工具和文档
5. **安全可靠**：环境变量管理，异步处理不阻塞

## 📝 开发日志

- **2026-04-03**：完成反馈系统开发和测试
  - 实现点赞/点踩完整流程
  - 修复浏览器缓存问题
  - 优化跨语言检索
  - 整理项目到独立目录

## 👥 维护者

- 开发：Claude Code + 用户协作
- 测试：完成基础功能测试
- 文档：完整的部署和使用文档

---

**注意事项**：
- ⚠️ 不要将 `.env` 文件提交到 Git
- ⚠️ Knowledge Base 数据源前缀需要匹配 `KB_S3_PREFIX` 配置
- ⚠️ DynamoDB 表创建后无法修改主键，请提前规划
