#!/bin/bash

# ============================================================================
# 更新 Lambda 执行角色策略 - 添加零配置 RBAC 权限
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}更新 Lambda 执行角色策略${NC}"
echo -e "${GREEN}========================================${NC}"

# 获取 Lambda 函数名
if [ -z "$1" ]; then
    echo -e "${YELLOW}请提供 Lambda 函数名称${NC}"
    echo "Usage: $0 <lambda-function-name>"
    echo "Example: $0 aws-support-case-lambda"
    exit 1
fi

LAMBDA_FUNCTION_NAME=$1

echo -e "\n${YELLOW}Step 1: 获取 Lambda 执行角色${NC}"
ROLE_NAME=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME \
    --region us-east-1 \
    --query 'Configuration.Role' --output text | awk -F'/' '{print $NF}')

if [ -z "$ROLE_NAME" ]; then
    echo -e "${RED}❌ 无法获取 Lambda 执行角色${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Lambda 执行角色: $ROLE_NAME${NC}"

echo -e "\n${YELLOW}Step 2: 更新角色策略（添加 RBAC 权限）${NC}"

aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name ZeroConfigRBACPolicy \
    --policy-document file://lambda_rbac_policy.json

echo -e "${GREEN}✓ 策略已更新${NC}"

echo -e "\n${YELLOW}Step 3: 验证策略${NC}"

aws iam get-role-policy \
    --role-name $ROLE_NAME \
    --policy-name ZeroConfigRBACPolicy \
    --query 'PolicyDocument.Statement[*].[Sid,Effect,Action]' \
    --output table

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 完成！${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}策略包含：${NC}"
echo "1. CloudWatch Logs 权限（记录日志）"
echo "2. IAM 查询权限（查询用户权限）"
echo "3. Support API 权限（调用 Support 服务）"

echo -e "\n${YELLOW}下一步：${NC}"
echo "1. 部署新的 Lambda Handler:"
echo "   python deploy_lambda.py"
echo ""
echo "2. 测试权限检查:"
echo "   python test_lambda.py --iam-user <your-iam-user>"
