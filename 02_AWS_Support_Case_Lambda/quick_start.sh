#!/bin/bash

# AWS Support Lambda - Quick Start Script
# 一键部署和测试

set -e  # 遇到错误立即退出

echo "=================================="
echo "AWS Support Lambda Quick Start"
echo "=================================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# 检查 AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI"
    exit 1
fi

# 检查 AWS 凭证
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Run 'aws configure'"
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# 步骤 1: 部署 Lambda
echo "Step 1/3: Deploying Lambda function..."
python3 deploy_lambda.py

if [ $? -ne 0 ]; then
    echo "❌ Lambda deployment failed"
    exit 1
fi

echo ""
echo "✅ Lambda deployed successfully"
echo ""

# 步骤 2: 运行测试
echo "Step 2/3: Running integration tests..."
echo "⚠️  Some tests may be skipped if you don't have active support cases"
echo ""

python3 test_lambda.py

echo ""

# 步骤 3: 提示下一步
echo "Step 3/3: Next Steps"
echo "=================================="
echo ""
echo "🎉 Lambda deployment completed!"
echo ""
echo "📋 Lambda Function Details:"
aws lambda get-function --function-name aws-support-tools-lambda \
  --query 'Configuration.[FunctionArn,Runtime,MemorySize,Timeout]' \
  --output text 2>/dev/null || echo "  (Run 'aws lambda get-function --function-name aws-support-tools-lambda' to view)"
echo ""
echo "📌 Next Steps:"
echo "1. Copy the Lambda ARN above"
echo "2. Add Lambda as a target in your AgentCore Gateway:"
echo "   - AWS Console → Bedrock → AgentCore → Gateways"
echo "   - Add Target → Lambda Function"
echo "   - Configure tool mappings for all 7 tools"
echo ""
echo "3. Update Agent code:"
echo "   - Edit: ../Agent/support_case_agent_lambda.py"
echo "   - Set LAMBDA_FUNCTION_ARN to your Lambda ARN"
echo "   - Redeploy your Agent"
echo ""
echo "4. Monitor Lambda execution:"
echo "   aws logs tail /aws/lambda/aws-support-tools-lambda --follow"
echo ""
echo "📚 Documentation:"
echo "   - Deployment Guide: ./README.md"
echo "   - Migration Guide: ../MIGRATION_GUIDE.md"
echo "   - Lambda Code: ./lambda_handler.py"
echo ""
echo "=================================="
