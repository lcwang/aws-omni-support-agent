#!/bin/bash

# 启动脚本 - 支持从 .env 文件或命令行参数读取配置
# 使用方法:
#   ./start.sh                          # 从 .env 文件读取
#   ./start.sh --kb-id XXX --bucket YYY # 从命令行传入

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "AWS Support Agent Web Client"
echo "=========================================="
echo ""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --kb-id)
            KNOWLEDGE_BASE_ID="$2"
            shift 2
            ;;
        --bucket)
            KB_S3_BUCKET="$2"
            shift 2
            ;;
        --agent-arn)
            AGENT_ARN="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--kb-id KB_ID] [--bucket S3_BUCKET] [--agent-arn ARN] [--port PORT]"
            exit 1
            ;;
    esac
done

# 尝试从 .env 文件读取配置（如果存在且未通过命令行指定）
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} 找到 .env 文件，加载配置..."
    set -a
    source .env
    set +a
else
    echo -e "${YELLOW}⚠${NC} 未找到 .env 文件"
    echo "  创建示例: cp .env.example .env"
fi

# 检查必需的配置
echo ""
echo "📋 配置检查:"
echo "  AWS Region: ${AWS_REGION:-us-east-1}"
echo "  Port: ${PORT:-8000}"

# Agent ARN
if [ -n "$AGENT_ARN" ]; then
    echo -e "  Agent ARN: ${GREEN}✓${NC} 已配置"
elif [ -f ../launch_result.pkl ]; then
    echo -e "  Agent ARN: ${GREEN}✓${NC} 从 launch_result.pkl 读取"
else
    echo -e "  Agent ARN: ${YELLOW}⚠${NC} 未配置（将尝试从 launch_result.pkl 读取）"
fi

# Knowledge Base
if [ -n "$KNOWLEDGE_BASE_ID" ] && [ -n "$KB_S3_BUCKET" ]; then
    echo -e "  Knowledge Base: ${GREEN}✓${NC} 已配置"
    echo "    - KB ID: $KNOWLEDGE_BASE_ID"
    echo "    - S3 Bucket: $KB_S3_BUCKET"
    export KNOWLEDGE_BASE_ID
    export KB_S3_BUCKET
else
    echo -e "  Knowledge Base: ${YELLOW}⚠${NC} 未配置（点赞更新 RAG 功能不可用）"
fi

# DynamoDB
if [ -n "$FEEDBACK_TABLE_NAME" ]; then
    echo -e "  DynamoDB 表: ${GREEN}✓${NC} $FEEDBACK_TABLE_NAME"
else
    export FEEDBACK_TABLE_NAME="support-agent-feedback-negative"
    echo -e "  DynamoDB 表: ${GREEN}✓${NC} $FEEDBACK_TABLE_NAME (默认)"
fi

echo ""
echo "=========================================="
echo "🚀 启动服务..."
echo "=========================================="

# 导出端口
export PORT="${PORT:-8000}"

# 启动 Python 应用
python3 app.py
