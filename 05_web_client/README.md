# AWS Support Agent Web Client

现代化的 Web 聊天界面，用于与 AWS AgentCore Runtime 进行交互。

## 特性

- **流式输出**: 实时显示 Agent 响应，无需等待完整回复
- **Markdown 渲染**: 支持富文本格式、代码高亮、列表等
- **现代化 UI**: 类似 ChatGPT/Gemini 的用户体验
- **响应式设计**: 支持桌面和移动设备
- **IAM Role 认证**: 部署到 EC2 时自动使用实例角色

## 快速开始

### 1. 安装依赖

```bash
cd web_client
pip install -r requirements.txt
# 或使用 uv
uv pip install -r requirements.txt
```

### 2. 配置 Agent ARN

有两种方式配置 Agent ARN：

**方式 1: 使用 launch_result.pkl**（推荐）

如果你已经运行了部署脚本，会在父目录生成 `launch_result.pkl`：

```bash
# 确保文件存在
ls -la ../launch_result.pkl
```

**方式 2: 环境变量**

```bash
export AGENT_ARN="arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT:runtime/YOUR_AGENT_ID"
export AWS_REGION="us-east-1"  # 可选，默认 us-east-1
```

### 3. 本地运行

```bash
python app.py
```

服务将在 http://localhost:8080 启动。

### 4. 访问界面

在浏览器中打开 http://localhost:8080

## 部署到 EC2

### 1. 创建 EC2 实例

选择 Amazon Linux 2023 或 Ubuntu，并附加 IAM Role，包含以下权限：

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:InvokeAgentRuntime"
            ],
            "Resource": "arn:aws:bedrock-agentcore:*:*:runtime/*"
        }
    ]
}
```

### 2. 安装依赖

SSH 到 EC2 实例：

```bash
# 更新系统
sudo yum update -y  # Amazon Linux
# 或
sudo apt update && sudo apt upgrade -y  # Ubuntu

# 安装 Python 3.11
sudo yum install python3.11 -y  # Amazon Linux
# 或
sudo apt install python3.11 python3.11-venv -y  # Ubuntu

# 克隆代码或上传文件
# ...

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# 安装依赖
cd web_client
uv pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
export AGENT_ARN="arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT:runtime/YOUR_AGENT_ID"
export PORT=8080
```

### 4. 运行服务

**方式 1: 直接运行**

```bash
python app.py
```

**方式 2: 使用 systemd（推荐）**

创建 systemd 服务文件：

```bash
sudo tee /etc/systemd/system/aws-support-agent.service > /dev/null <<EOF
[Unit]
Description=AWS Support Agent Web Client
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/web_client
Environment="AGENT_ARN=arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT:runtime/YOUR_AGENT_ID"
Environment="PORT=8080"
ExecStart=/usr/bin/python3 /home/ec2-user/web_client/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable aws-support-agent
sudo systemctl start aws-support-agent

# 查看状态
sudo systemctl status aws-support-agent

# 查看日志
sudo journalctl -u aws-support-agent -f
```

**方式 3: 使用 Screen（临时测试）**

```bash
screen -S agent
python app.py
# Ctrl+A, D 退出 screen
# screen -r agent 重新连接
```

### 5. 配置反向代理（可选）

使用 Nginx 作为反向代理，支持 HTTPS：

```bash
# 安装 Nginx
sudo yum install nginx -y  # Amazon Linux
# 或
sudo apt install nginx -y  # Ubuntu

# 配置 Nginx
sudo tee /etc/nginx/conf.d/agent.conf > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
    }
}
EOF

# 启动 Nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 6. 配置防火墙

```bash
# 开放 80 端口（HTTP）
sudo firewall-cmd --permanent --add-service=http  # Amazon Linux
sudo ufw allow 80  # Ubuntu

# 或在 EC2 Security Group 中添加规则
```

## 使用说明

### 基本操作

1. 在输入框中输入问题
2. 按 Enter 发送（Shift+Enter 换行）
3. 等待 Agent 流式返回响应

### 示例问题

```
帮我查看一下过去三个月的case并总结给我

创建一个新的 support case：
- 问题: Lambda 函数超时
- 严重程度: high
- 服务: Lambda

查询 case ID 为 12345678 的详细信息
```

## 目录结构

```
web_client/
├── app.py                 # FastAPI 后端
├── requirements.txt       # Python 依赖
├── README.md             # 本文件
├── static/
│   ├── style.css         # CSS 样式
│   └── script.js         # JavaScript 前端逻辑
└── templates/
    └── index.html        # HTML 主页面
```

## 技术栈

- **后端**: FastAPI + Uvicorn
- **前端**: Vanilla JavaScript + Marked.js + Highlight.js
- **AWS SDK**: Boto3
- **样式**: 原生 CSS（无框架）

## 故障排除

### 问题 1: 无法连接到 Agent

**检查**:
```bash
# 查看状态指示器
# 如果显示 "Error"，检查后端日志

# 检查 Agent ARN
curl http://localhost:8080/health

# 查看环境变量
echo $AGENT_ARN
```

### 问题 2: 流式输出不工作

**可能原因**:
- Nginx 缓冲未关闭（确保 `proxy_buffering off`）
- 防火墙阻止了 SSE 连接
- Agent Runtime 未返回流式响应

**检查**:
```bash
# 测试直接访问（绕过 Nginx）
curl http://localhost:8080/health

# 查看浏览器 Console
# F12 → Console → 查看错误
```

### 问题 3: IAM 权限错误

**错误信息**:
```
Error: AccessDeniedException: User is not authorized to perform: bedrock-agentcore:InvokeAgentRuntime
```

**解决**:
```bash
# 检查 EC2 实例角色
aws sts get-caller-identity

# 确认角色权限
# 在 IAM Console 中查看实例角色是否有 bedrock-agentcore:InvokeAgentRuntime 权限
```

## 开发

### 修改前端

编辑 `static/style.css` 或 `static/script.js`，刷新浏览器即可看到效果。

### 修改后端

编辑 `app.py`，需要重启服务：

```bash
# 如果使用 systemd
sudo systemctl restart aws-support-agent

# 如果直接运行
# Ctrl+C 停止，然后重新运行 python app.py
```

### 添加新功能

1. 后端 API: 在 `app.py` 中添加新的路由
2. 前端交互: 在 `script.js` 中添加逻辑
3. 样式调整: 在 `style.css` 中修改

## 性能优化

- 使用 Nginx 作为反向代理
- 启用 gzip 压缩
- 使用 CDN 加载第三方库
- 配置 HTTP/2

## 安全建议

- 使用 HTTPS（Let's Encrypt）
- 限制来源 IP（Security Group）
- 启用 CloudWatch 日志
- 定期更新依赖

## License

MIT
