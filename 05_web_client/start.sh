#!/bin/bash

# 启动 Web Client
cd "$(dirname "$0")"

echo "🚀 Starting AWS Support Agent Web Client..."
echo ""

# 检查 AGENT_ARN
if [ -z "$AGENT_ARN" ]; then
    echo "⚠️  AGENT_ARN not set. Using test mode."
    echo "To use real agent, run:"
    echo "  export AGENT_ARN='arn:aws:bedrock:REGION:ACCOUNT_ID:agent/YOUR_AGENT_ID'"
    echo ""
    export TEST_MODE=1
fi

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Please run:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# 启动服务
python3 app.py
