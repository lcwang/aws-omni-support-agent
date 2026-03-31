#!/bin/bash

# ============================================================================
# 零配置 RBAC 一键部署脚本
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}    零配置 RBAC 部署脚本${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 检查参数
if [ -z "$1" ]; then
    echo -e "${RED}❌ 请提供 Lambda 函数名称${NC}"
    echo "Usage: $0 <lambda-function-name> [iam-user-for-test]"
    echo "Example: $0 aws-support-case-lambda alice"
    exit 1
fi

LAMBDA_FUNCTION_NAME=$1
IAM_USER_FOR_TEST=${2:-""}

echo ""
echo -e "${GREEN}Lambda 函数: ${LAMBDA_FUNCTION_NAME}${NC}"
if [ -n "$IAM_USER_FOR_TEST" ]; then
    echo -e "${GREEN}测试用户: ${IAM_USER_FOR_TEST}${NC}"
fi
echo ""

# ============================================================================
# Step 1: 更新 Lambda 执行角色策略
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 1: 更新 Lambda 执行角色策略${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo "获取 Lambda 执行角色..."
ROLE_NAME=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME \
    --region us-east-1 \
    --query 'Configuration.Role' --output text | awk -F'/' '{print $NF}')

if [ -z "$ROLE_NAME" ]; then
    echo -e "${RED}❌ 无法获取 Lambda 执行角色${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Lambda 执行角色: ${ROLE_NAME}${NC}"

echo "更新角色策略（添加 IAM 查询和 Support API 权限）..."
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name ZeroConfigRBACPolicy \
    --policy-document file://lambda_rbac_policy.json

echo -e "${GREEN}✓ 策略已更新${NC}"

# ============================================================================
# Step 2: 备份现有 Lambda Handler
# ============================================================================
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 2: 备份现有 Lambda Handler${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "lambda_handler_backup.py" ]; then
    echo -e "${YELLOW}⚠️  备份文件已存在，跳过备份${NC}"
else
    echo "备份 lambda_handler.py..."
    cp lambda_handler.py lambda_handler_backup.py
    echo -e "${GREEN}✓ 已备份到 lambda_handler_backup.py${NC}"
fi

# ============================================================================
# Step 3: 部署新的 Lambda Handler
# ============================================================================
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 3: 部署新的 Lambda Handler${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo "检查是否已经是 RBAC 版本..."
if grep -q "零配置 RBAC" lambda_handler.py; then
    echo -e "${GREEN}✓ lambda_handler.py 已经是零配置 RBAC 版本${NC}"
else
    echo -e "${RED}❌ lambda_handler.py 不是零配置 RBAC 版本${NC}"
    echo "请确保已经修改了 lambda_handler.py"
    exit 1
fi

if [ -f "deploy_lambda.py" ]; then
    echo "使用 deploy_lambda.py 部署..."
    python3 deploy_lambda.py
    echo -e "${GREEN}✓ Lambda 已部署${NC}"
else
    echo -e "${YELLOW}⚠️  deploy_lambda.py 不存在，请手动部署 Lambda${NC}"
fi

# ============================================================================
# Step 4: 运行测试（如果提供了测试用户）
# ============================================================================
if [ -n "$IAM_USER_FOR_TEST" ]; then
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Step 4: 运行测试${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # 等待 Lambda 更新生效
    echo "等待 5 秒让 Lambda 更新生效..."
    sleep 5

    echo "运行测试（跳过创建真实工单）..."
    python3 test_rbac.py \
        --lambda-name $LAMBDA_FUNCTION_NAME \
        --iam-user $IAM_USER_FOR_TEST \
        --skip-create

    echo ""
    echo -e "${GREEN}✓ 测试完成${NC}"
fi

# ============================================================================
# 完成
# ============================================================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 部署完成！${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo -e "${YELLOW}已完成配置：${NC}"
echo "  1. ✓ Lambda 执行角色策略（IAM 查询 + Support API）"
echo "  2. ✓ Lambda Handler（零配置 RBAC 版本）"
if [ -n "$IAM_USER_FOR_TEST" ]; then
    echo "  3. ✓ 权限测试"
fi

echo ""
echo -e "${YELLOW}零配置 RBAC 工作原理：${NC}"
echo "  • QA 工具（describe_*）无需鉴权，所有人可用"
echo "  • Case 写入工具需要传递 _iam_user 参数"
echo "  • Lambda 查询用户的 IAM Policy 检查权限"
echo "  • 有权限 → 执行，无权限 → 返回 403"
echo "  • 审计日志记录在 CloudWatch Logs"

echo ""
echo -e "${YELLOW}下一步：${NC}"
echo "  1. 更新 Agent Runtime，传递 _iam_user 参数"
echo "  2. 确保用户已有 AWS Support 权限配置"
echo "  3. 测试完整流程："
echo "     python test_rbac.py --lambda-name $LAMBDA_FUNCTION_NAME --iam-user <your-user>"

echo ""
echo -e "${YELLOW}查看审计日志：${NC}"
echo "  aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --follow --filter-pattern \"[AUDIT]\""

echo ""
