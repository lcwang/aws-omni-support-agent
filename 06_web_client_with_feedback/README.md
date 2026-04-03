# AWS Support Agent - Web Client with Feedback System

> 整合版本 - Web 客户端 + 反馈系统

**创建时间**: 2026-04-03
**状态**: ✅ Ready to use


---

## 📁 目录结构

```
06_web_client_with_feedback/
├── README.md                       # 本文件
├── requirements.txt                # 统一的依赖文件
├── app.py                          # 主应用（不再需要 sys.path.append）
│
├── templates/                      # 前端模板
│   └── index.html                  # Web UI
│
├── static/                         # 静态文件
│   ├── style.css                   # 样式
│   ├── script.js                   # 主脚本
│   ├── session-styles.css          # 会话样式
│   ├── feedback-ui.js              # 反馈 UI 逻辑
│   └── feedback-ui.css             # 反馈 UI 样式
│
├── feedback/                       # 反馈系统模块（Python 包）
│   ├── __init__.py                 # 包初始化
│   ├── config.py                   # 配置管理
│   ├── models.py                   # 数据模型
│   ├── api.py                      # API 端点
│   │
│   ├── handlers/                   # 反馈处理器
│   │   ├── __init__.py
│   │   ├── positive_handler.py     # 点赞处理
│   │   └── negative_handler.py     # 点踩处理
│   │
│   └── operations/                 # 数据操作层
│       ├── __init__.py
│       ├── dynamodb_operations.py  # DynamoDB CRUD
│       └── bedrock_kb_operations.py # Bedrock KB 操作
│
├── deployment/                     # 部署相关
│   ├── setup_dynamodb.py           # DynamoDB 表创建脚本
│   └── DYNAMODB_SETUP_GUIDE.md     # DynamoDB 详细指南
│
└── docs/                           # 文档
    ├── QUICKSTART.md               # 快速开始
    ├── ARCHITECTURE.md             # 架构说明
    └── ... (更多文档)
```

---

## 🚀 快速开始

### 1. 创建虚拟环境

```bash
# 进入项目根目录
cd /Users/havpan/CC_Demo/aws-omni-support-agent-v2

# 创建虚拟环境（推荐使用 uv）
uv venv 

# 激活虚拟环境
source .venv/bin/activate
```

📖 **详细指南**: [../ENVIRONMENT_SETUP.md](../ENVIRONMENT_SETUP.md)

---

### 2. 安装依赖

```bash
cd 06_web_client_with_feedback

# 使用 uv（推荐）
uv pip install -r requirements.txt

# 或使用 pip
pip install -r requirements.txt
```

---

### 3. 验证 DynamoDB 表

```bash
# 检查表是否已创建
aws dynamodb describe-table \
  --table-name support-agent-feedback-negative \
  --region us-east-1 \
  --query 'Table.TableStatus'

# 如果表不存在，创建它
cd deployment
python3 setup_dynamodb.py
cd ..
```

📖 **详细指南**: [deployment/DYNAMODB_SETUP_GUIDE.md](deployment/DYNAMODB_SETUP_GUIDE.md)

---

### 4. 启动服务

```bash
# 确保在 06_web_client_with_feedback 目录
python3 app.py

# 或使用 uvicorn
uvicorn app:app --reload --port 8000
```

---

### 5. 测试

访问 http://localhost:8000

- ✅ 发送消息
- ✅ 点击 👍 或 👎 按钮
- ✅ 查看反馈是否成功提交

验证 DynamoDB:
```bash
aws dynamodb scan \
  --table-name support-agent-feedback-negative \
  --limit 5
```

---

## 🔧 配置

### 必需配置

**DynamoDB 表** - 已创建 ✅
- 表名: `support-agent-feedback-negative`
- 用途: 存储点踩反馈

### 可选配置

**Bedrock Knowledge Base** - 用于点赞更新 RAG

在 `app.py` 启动前添加（在 `if __name__ == "__main__":` 部分）:

```python
if __name__ == "__main__":
    import uvicorn

    # ... 其他代码 ...

    # 配置 Bedrock KB（可选）
    if FEEDBACK_ENABLED:
        try:
            from feedback.operations import configure_kb
            configure_kb(
                knowledge_base_id="YOUR_KB_ID",
                s3_bucket="YOUR_S3_BUCKET"
            )
            print(f"✅ Knowledge Base configured")
        except Exception as e:
            print(f"⚠️ Knowledge Base not configured: {e}")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
```

查看 Knowledge Base ID:
```bash
aws bedrock-agent list-knowledge-bases --region us-east-1
```

---

## ✨ 关键改进

### 1. 不再需要 sys.path.append

**旧方式** (05_web_client/app.py):
```python
# ❌ 需要动态添加路径
sys.path.append(str(Path(__file__).resolve().parent.parent / '06_feedback' / 'backend'))
from models import FeedbackRequest
from api import submit_feedback
```

**新方式** (06_web_client_with_feedback/app.py):
```python
# ✅ 标准 Python 导入
from feedback import FeedbackRequest, submit_feedback, health_check, get_feedback_stats
```

---

### 2. 标准 Python 包结构

`feedback/` 现在是一个标准的 Python 包：
- ✅ 有 `__init__.py`
- ✅ 使用相对导入 (`.models`, `.config`)
- ✅ 可以作为模块导入
- ✅ 符合 Python 最佳实践

---

### 3. 统一依赖管理

只需要一个 `requirements.txt`:
```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
boto3>=1.40.0
pydantic>=2.5.0
jinja2==3.1.5
python-dateutil>=2.8.2
python-multipart==0.0.20
```

---

## 🔄 与原方案的对应关系

| 原文件位置 | 新文件位置 |
|-----------|-----------|
| `05_web_client/app.py` | `06_web_client_with_feedback/app.py` |
| `05_web_client/templates/` | `06_web_client_with_feedback/templates/` |
| `05_web_client/static/` | `06_web_client_with_feedback/static/` |
| `06_feedback/backend/models.py` | `06_web_client_with_feedback/feedback/models.py` |
| `06_feedback/backend/api.py` | `06_web_client_with_feedback/feedback/api.py` |
| `06_feedback/backend/handlers/` | `06_web_client_with_feedback/feedback/handlers/` |
| `06_feedback/backend/operations/` | `06_web_client_with_feedback/feedback/operations/` |
| `06_feedback/deployment/` | `06_web_client_with_feedback/deployment/` |

---

## 📚 文档

### 快速上手
- [../ENVIRONMENT_SETUP.md](../ENVIRONMENT_SETUP.md) - 环境配置（虚拟环境、依赖）
- [deployment/DYNAMODB_SETUP_GUIDE.md](deployment/DYNAMODB_SETUP_GUIDE.md) - DynamoDB 创建指南

### 原 06_feedback 文档
原 `06_feedback/` 目录下的所有文档仍然适用，只是导入路径有所变化：

- `06_feedback/QUICKSTART.md` - 快速开始
- `06_feedback/ARCHITECTURE.md` - 架构说明
- `06_feedback/INTEGRATION_GUIDE.md` - 集成指南
- `06_feedback/FAQ.md` - 常见问题
- `06_feedback/DOCUMENTATION_INDEX.md` - 文档索引

---

## 🧪 测试

### 测试导入

```bash
python3 -c "
from feedback import FeedbackRequest, submit_feedback
from feedback.operations import configure_kb
from feedback.handlers import handle_positive_feedback
print('✅ All imports successful')
"
```

### 测试启动

```bash
# 启动服务（3 秒后自动退出）
timeout 3 python3 app.py || echo "✅ Server starts successfully"
```

### 测试反馈 API

```bash
# 启动服务
python3 app.py &
APP_PID=$!

# 等待启动
sleep 3

# 测试健康检查
curl http://localhost:8000/api/feedback/health | jq

# 停止服务
kill $APP_PID
```

---

## ❓ 常见问题

### Q1: 我应该使用 05+06 还是 07？

**答案**: 推荐使用 **07**（整合版）

| 场景 | 推荐 |
|------|------|
| 新部署 | ✅ 使用 07 |
| 现有项目（05+06） | 可以继续使用，也可以迁移到 07 |
| 开发和维护 | ✅ 使用 07（更清晰）|

---

### Q2: 如何从 05+06 迁移到 07？

**答案**: 已经帮你整合好了！

只需要：
1. 使用 `06_web_client_with_feedback/` 替代 `05_web_client/`
2. 不再需要单独的 `06_feedback/` 目录
3. DynamoDB 表继续使用（无需变化）

---

### Q3: 导入错误怎么办？

**症状**: `ModuleNotFoundError: No module named 'feedback'`

**原因**: 不在正确的目录或虚拟环境未激活

**解决**:
```bash
# 1. 确认目录
pwd  # 应该显示 .../06_web_client_with_feedback

# 2. 确认虚拟环境
which python3  # 应该显示 .venv/bin/python3

# 3. 确认依赖
pip list | grep pydantic

# 4. 测试导入
python3 -c "from feedback import FeedbackRequest; print('OK')"
```

---

## 🎓 技术说明

### Python 包结构

```python
# feedback/ 是一个标准的 Python 包
feedback/
├── __init__.py          # 定义包的公共 API
├── config.py            # 配置
├── models.py            # 数据模型
├── api.py               # API 端点
├── handlers/            # 子包
│   ├── __init__.py
│   ├── positive_handler.py
│   └── negative_handler.py
└── operations/          # 子包
    ├── __init__.py
    ├── dynamodb_operations.py
    └── bedrock_kb_operations.py
```

### 相对导入

```python
# 在 feedback/handlers/positive_handler.py 中
from ..models import FeedbackRequest         # 从父包导入
from ..operations import configure_kb        # 从兄弟包导入
from ..config import AWS_REGION             # 从父包导入
```

### 绝对导入

```python
# 在 app.py 中
from feedback import FeedbackRequest         # 从包导入
from feedback.operations import configure_kb # 从子包导入
```

---

## 📞 获取帮助

遇到问题？

1. 查看 [../ENVIRONMENT_SETUP.md](../ENVIRONMENT_SETUP.md)
2. 查看 [../06_feedback/FAQ.md](../06_feedback/FAQ.md)
3. 检查 Python 版本: `python3 --version` (应该 ≥3.11)
4. 检查虚拟环境: `which python3`
5. 检查依赖: `pip list`

---

**版本**: 1.0
**最后更新**: 2026-04-03
**维护者**: AWS Omni Support Agent Team
