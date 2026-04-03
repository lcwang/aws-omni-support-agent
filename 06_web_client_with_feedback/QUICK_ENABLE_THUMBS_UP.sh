#!/bin/bash

# 快速开启点赞更新 RAG 功能
# 使用方法: ./QUICK_ENABLE_THUMBS_UP.sh

set -e

echo "=========================================="
echo "点赞更新 RAG 功能 - 快速配置"
echo "=========================================="
echo ""

# 1. 获取 Knowledge Base ID
echo "📋 步骤 1/3: 获取 Knowledge Base ID"
echo ""
echo "运行以下命令查看你的 Knowledge Bases:"
echo ""
echo "  aws bedrock-agent list-knowledge-bases --region us-east-1 \\"
echo "    --query 'knowledgeBaseSummaries[*].[name,knowledgeBaseId]' \\"
echo "    --output table"
echo ""
read -p "请输入你的 Knowledge Base ID (例如: ABCDEFGHIJ): " KB_ID

if [ -z "$KB_ID" ]; then
    echo "❌ Knowledge Base ID 不能为空"
    exit 1
fi

echo "✅ Knowledge Base ID: $KB_ID"
echo ""

# 2. 获取 S3 Bucket
echo "📋 步骤 2/3: 获取 S3 Bucket 名称"
echo ""
echo "运行以下命令查看 Knowledge Base 的数据源:"
echo ""
echo "  aws bedrock-agent list-data-sources \\"
echo "    --knowledge-base-id $KB_ID \\"
echo "    --region us-east-1"
echo ""
read -p "请输入 S3 Bucket 名称（不是ARN，例如: my-kb-data-source): " S3_BUCKET

if [ -z "$S3_BUCKET" ]; then
    echo "❌ S3 Bucket 不能为空"
    exit 1
fi

echo "✅ S3 Bucket: $S3_BUCKET"
echo ""

# 3. 创建或更新 .env 文件
echo "📋 步骤 3/3: 配置环境变量"
echo ""

# 检查 .env 是否存在
if [ -f .env ]; then
    echo "⚠️  发现已存在的 .env 文件"
    read -p "是否备份并更新？(y/n): " BACKUP
    if [ "$BACKUP" = "y" ]; then
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        echo "✅ 已备份到 .env.backup.$(date +%Y%m%d_%H%M%S)"
    else
        echo "❌ 取消操作"
        exit 1
    fi
else
    # 从 .env.example 复制
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ 从 .env.example 创建 .env 文件"
    else
        touch .env
        echo "✅ 创建新的 .env 文件"
    fi
fi

# 更新或添加配置
if grep -q "^KNOWLEDGE_BASE_ID=" .env; then
    # macOS 和 Linux 的 sed 语法不同
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^KNOWLEDGE_BASE_ID=.*|KNOWLEDGE_BASE_ID=$KB_ID|" .env
        sed -i '' "s|^KB_S3_BUCKET=.*|KB_S3_BUCKET=$S3_BUCKET|" .env
    else
        sed -i "s|^KNOWLEDGE_BASE_ID=.*|KNOWLEDGE_BASE_ID=$KB_ID|" .env
        sed -i "s|^KB_S3_BUCKET=.*|KB_S3_BUCKET=$S3_BUCKET|" .env
    fi
    echo "✅ 已更新 .env 文件中的配置"
else
    # 追加配置
    echo "" >> .env
    echo "# Knowledge Base 配置（通过 QUICK_ENABLE_THUMBS_UP.sh 添加）" >> .env
    echo "KNOWLEDGE_BASE_ID=$KB_ID" >> .env
    echo "KB_S3_BUCKET=$S3_BUCKET" >> .env
    echo "KB_S3_PREFIX=validated-qa/" >> .env
    echo "✅ 已添加配置到 .env 文件"
fi

echo ""

# 4. 验证配置
echo "=========================================="
echo "配置完成！"
echo "=========================================="
echo ""
echo "📝 配置摘要:"
echo "  Knowledge Base ID: $KB_ID"
echo "  S3 Bucket: $S3_BUCKET"
echo "  S3 Prefix: validated-qa/ (默认)"
echo "  配置位置: .env 文件"
echo ""
echo "🚀 下一步:"
echo "  1. 启动服务: ./start.sh"
echo "  2. 查看启动日志，确认看到："
echo "     ✓ 找到 .env 文件，加载配置..."
echo "     Knowledge Base: ✓ 已配置"
echo "  3. 测试点赞功能"
echo ""
echo "🔍 查看配置:"
echo "  cat .env"
echo ""
echo "📚 详细文档: THUMBS_UP_RAG_SETUP.md"
echo ""
