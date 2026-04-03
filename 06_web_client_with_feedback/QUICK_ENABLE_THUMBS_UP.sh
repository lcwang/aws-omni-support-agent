#!/bin/bash

# 快速开启点赞更新 RAG 功能
# 使用方法: ./QUICK_ENABLE_THUMBS_UP.sh

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
read -p "请输入你的 Knowledge Base ID (例如: YOUR_KB_ID): " KB_ID

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

# 3. 修改 app.py
echo "📋 步骤 3/3: 修改配置文件"
echo ""

# 备份原文件
cp app.py app.py.backup
echo "✅ 已备份原文件到 app.py.backup"

# 使用 sed 修改配置
# macOS 和 Linux 的 sed 语法不同，需要兼容处理
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/knowledge_base_id=\"YOUR_KB_ID\"/knowledge_base_id=\"$KB_ID\"/g" app.py
    sed -i '' "s/s3_bucket=\"YOUR_S3_BUCKET\"/s3_bucket=\"$S3_BUCKET\"/g" app.py
    sed -i '' 's/# if FEEDBACK_ENABLED:/if FEEDBACK_ENABLED:/g' app.py
    sed -i '' 's/#     try:/    try:/g' app.py
    sed -i '' 's/#         from feedback.operations import configure_kb/        from feedback.operations import configure_kb/g' app.py
    sed -i '' 's/#         configure_kb(/        configure_kb(/g' app.py
    sed -i '' 's/#             knowledge_base_id/            knowledge_base_id/g' app.py
    sed -i '' 's/#             s3_bucket/            s3_bucket/g' app.py
    sed -i '' 's/#         )/        )/g' app.py
    sed -i '' 's/#         print(f"✅ Knowledge Base configured/        print(f"✅ Knowledge Base configured/g' app.py
    sed -i '' 's/#     except Exception as e:/    except Exception as e:/g' app.py
    sed -i '' 's/#         print(f"⚠️  Knowledge Base not configured/        print(f"⚠️  Knowledge Base not configured/g' app.py
else
    # Linux
    sed -i "s/knowledge_base_id=\"YOUR_KB_ID\"/knowledge_base_id=\"$KB_ID\"/g" app.py
    sed -i "s/s3_bucket=\"YOUR_S3_BUCKET\"/s3_bucket=\"$S3_BUCKET\"/g" app.py
    sed -i 's/# if FEEDBACK_ENABLED:/if FEEDBACK_ENABLED:/g' app.py
    sed -i 's/#     try:/    try:/g' app.py
    sed -i 's/#         from feedback.operations import configure_kb/        from feedback.operations import configure_kb/g' app.py
    sed -i 's/#         configure_kb(/        configure_kb(/g' app.py
    sed -i 's/#             knowledge_base_id/            knowledge_base_id/g' app.py
    sed -i 's/#             s3_bucket/            s3_bucket/g' app.py
    sed -i 's/#         )/        )/g' app.py
    sed -i 's/#         print(f"✅ Knowledge Base configured/        print(f"✅ Knowledge Base configured/g' app.py
    sed -i 's/#     except Exception as e:/    except Exception as e:/g' app.py
    sed -i 's/#         print(f"⚠️  Knowledge Base not configured/        print(f"⚠️  Knowledge Base not configured/g' app.py
fi

echo "✅ 已更新 app.py"
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
echo ""
echo "🚀 下一步:"
echo "  1. 启动服务: python3 app.py"
echo "  2. 查看启动日志，确认看到："
echo "     ✅ Knowledge Base configured for feedback RAG updates"
echo "  3. 测试点赞功能"
echo ""
echo "🔍 如需回滚:"
echo "  mv app.py.backup app.py"
echo ""
echo "📚 详细文档: THUMBS_UP_RAG_SETUP.md"
echo ""
