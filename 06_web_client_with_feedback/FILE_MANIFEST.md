# 文件清单

本文档列出了 `06_web_client_with_feedback` 目录中的所有文件及其用途。

## 📂 目录结构总览

```
06_web_client_with_feedback/
├── 配置文件 (3)
├── 核心代码 (1 + feedback 包)
├── 前端资源 (6)
├── 文档 (7)
├── 工具脚本 (3)
└── 部署资源 (2)

总计：33 个文件
```

---

## 📋 详细文件列表

### 🔧 配置文件 (3个)

| 文件 | 状态 | 说明 |
|------|------|------|
| `.env.example` | ✅ 必需 | 环境变量配置模板 |
| `.gitignore` | ✅ 必需 | Git 忽略规则（防止敏感文件提交）|
| `requirements.txt` | ✅ 必需 | Python 依赖列表 |

---

### 💻 核心代码 (15个)

#### 主应用

| 文件 | 行数 | 说明 |
|------|------|------|
| `app.py` | ~450 | FastAPI 主应用（对话 + 反馈 API）|

#### Feedback 包

**Package 初始化：**
| 文件 | 说明 |
|------|------|
| `feedback/__init__.py` | 导出公共 API |
| `feedback/handlers/__init__.py` | 导出 Handler |
| `feedback/operations/__init__.py` | 导出 Operations |

**核心模块：**
| 文件 | 行数 | 说明 |
|------|------|------|
| `feedback/api.py` | ~150 | 反馈 API 入口（submit_feedback 等）|
| `feedback/config.py` | ~100 | 配置管理（环境变量 + 验证）|
| `feedback/models.py` | ~150 | Pydantic 数据模型（FeedbackRequest 等）|

**Handler 层：**
| 文件 | 行数 | 说明 |
|------|------|------|
| `feedback/handlers/positive_handler.py` | ~220 | 点赞处理（分类 + S3 上传 + KB ingestion）|
| `feedback/handlers/negative_handler.py` | ~180 | 点踩处理（分类 + DynamoDB 存储）|

**Operations 层：**
| 文件 | 行数 | 说明 |
|------|------|------|
| `feedback/operations/bedrock_kb_operations.py` | ~330 | Bedrock KB 操作（S3 + ingestion + 去重）|
| `feedback/operations/dynamodb_operations.py` | ~350 | DynamoDB CRUD（存储 + 查询 + 更新）|
| `feedback/operations/opensearch_operations.py` | ~200 | OpenSearch 操作（备用方案，未启用）|

---

### 🎨 前端资源 (7个)

#### HTML

| 文件 | 说明 |
|------|------|
| `templates/index.html` | 主页面（包含点踩弹窗 HTML）|

#### JavaScript

| 文件 | 行数 | 说明 |
|------|------|------|
| `static/script.js` | ~690 | 主逻辑（对话 + 流式输出 + Session 管理）|
| `static/feedback-ui.js` | ~150 | 反馈 UI 逻辑（按钮点击 + 弹窗管理）|
| `static/debug.js` | ~50 | 前端调试工具 |

#### CSS

| 文件 | 说明 |
|------|------|
| `static/style.css` | 主样式 |
| `static/session-styles.css` | Session 相关样式 |
| `static/feedback-ui.css` | 反馈按钮和弹窗样式 |

---

### 📚 文档 (8个)

| 文件 | 行数 | 用途 |
|------|------|------|
| `README.md` | ~300 | 项目主文档（功能 + 快速开始）|
| `PROJECT_SUMMARY.md` | ~400 | 项目总结（架构 + 技术点 + 对比）|
| `FILE_MANIFEST.md` | ~200 | 本文件（文件清单）|
| `ENV_CONFIG_GUIDE.md` | ~200 | 环境变量配置完整指南 |
| `THUMBS_UP_RAG_SETUP.md` | ~300 | 点赞更新 RAG 详细说明 |
| `COMPARISON.md` | ~250 | Feedback 实现方案对比 |
| `RETRIEVAL_TRACKING_GUIDE.md` | ~300 | 检索结果追踪方案 |
| `deployment/DYNAMODB_SETUP_GUIDE.md` | ~150 | DynamoDB 表创建指南 |

---

### 🛠️ 工具脚本 (3个)

| 文件 | 行数 | 说明 |
|------|------|------|
| `start.sh` | ~80 | 启动脚本（加载 .env + 启动服务）|
| `QUICK_ENABLE_THUMBS_UP.sh` | ~120 | 快速启用点赞功能脚本 |
| `debug_kb_ingestion.py` | ~300 | KB ingestion 诊断工具（6步诊断）|

---

### 🚀 部署资源 (2个)

| 文件 | 行数 | 说明 |
|------|------|------|
| `deployment/setup_dynamodb.py` | ~150 | 自动创建 DynamoDB 表（含 GSI）|
| `deployment/DYNAMODB_SETUP_GUIDE.md` | ~150 | DynamoDB 部署完整指南 |

---

## 📊 统计信息

| 类型 | 数量 | 总行数（估算）|
|------|------|---------------|
| Python 文件 | 14 | ~3,200 |
| JavaScript 文件 | 3 | ~890 |
| CSS 文件 | 3 | ~500 |
| HTML 文件 | 1 | ~190 |
| Markdown 文档 | 8 | ~2,100 |
| Shell 脚本 | 2 | ~200 |
| 配置文件 | 2 | ~50 |
| **总计** | **33** | **~7,130** |

---

## 🔍 文件用途索引

### 快速查找指南

**想要了解...**  → **查看文件...**

- **如何启动？** → `README.md` + `start.sh`
- **如何配置？** → `ENV_CONFIG_GUIDE.md` + `.env.example`
- **点赞如何工作？** → `THUMBS_UP_RAG_SETUP.md` + `feedback/handlers/positive_handler.py`
- **点踩如何工作？** → `feedback/handlers/negative_handler.py`
- **DynamoDB 如何创建？** → `deployment/DYNAMODB_SETUP_GUIDE.md` + `deployment/setup_dynamodb.py`
- **KB ingestion 问题？** → `debug_kb_ingestion.py`
- **API 如何调用？** → `feedback/api.py`
- **数据模型？** → `feedback/models.py`
- **前端逻辑？** → `static/script.js` + `static/feedback-ui.js`
- **架构设计？** → `PROJECT_SUMMARY.md`

---

## ✅ 推送前检查清单

在推送到 GitHub 之前，请确认：

- [ ] ✅ `.env` 文件已删除（不在目录中）
- [ ] ✅ `.gitignore` 文件已添加
- [ ] ✅ 所有 `__pycache__/` 目录已清理
- [ ] ✅ `.env.example` 包含所有必需的配置项（但无真实值）
- [ ] ✅ README.md 准确描述项目功能
- [ ] ✅ 所有敏感信息（Account ID、Agent ARN）已移除

---

## 📝 版本信息

- **创建日期**：2026-04-03
- **版本**：1.0.0
- **目录名**：06_web_client_with_feedback
- **状态**：已完成开发和测试，准备推送

---

## 🚫 不应推送的文件（已清理）

以下文件**不在**此目录中，**不会**被推送：

- ❌ `.env` - 包含敏感信息
- ❌ `__pycache__/` - Python 编译缓存
- ❌ `*.pyc` - Python 字节码文件
- ❌ `.DS_Store` - macOS 系统文件

这些文件已在 `.gitignore` 中配置，即使意外创建也不会被 Git 追踪。

---

**准备完毕，可以推送！** 🚀
