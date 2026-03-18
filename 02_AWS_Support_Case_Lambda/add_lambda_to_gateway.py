#!/usr/bin/env python3
"""
将 Lambda 添加到 AgentCore Gateway 的脚本
由于 AWS CLI 暂不支持 bedrock-agentcore，使用 boto3 SDK
"""

import boto3
import json
import os
import sys

# 配置 - 从环境变量读取，如果未设置则提示用户输入
GATEWAY_ARN = os.environ.get('GATEWAY_ARN')
LAMBDA_ARN = os.environ.get('LAMBDA_ARN')

# 如果环境变量未设置，尝试从命令行参数获取
if not GATEWAY_ARN or not LAMBDA_ARN:
    if len(sys.argv) >= 3:
        GATEWAY_ARN = sys.argv[1]
        LAMBDA_ARN = sys.argv[2]
    else:
        print("❌ 缺少必要配置\n")
        print("请使用以下方式之一提供配置:\n")
        print("方式 1 - 环境变量:")
        print("  export GATEWAY_ARN='arn:aws:bedrock-agentcore:REGION:ACCOUNT:gateway/GATEWAY_ID'")
        print("  export LAMBDA_ARN='arn:aws:lambda:REGION:ACCOUNT:function:FUNCTION_NAME'")
        print("  python add_lambda_to_gateway.py\n")
        print("方式 2 - 命令行参数:")
        print("  python add_lambda_to_gateway.py <GATEWAY_ARN> <LAMBDA_ARN>\n")
        print("示例:")
        print("  python add_lambda_to_gateway.py \\")
        print("    'arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/gateway-xxxxx' \\")
        print("    'arn:aws:lambda:us-east-1:123456789012:function:aws-support-tools-lambda'")
        sys.exit(1)

# 从 Gateway ARN 中提取 region
GATEWAY_REGION = GATEWAY_ARN.split(':')[3]

# 7个工具的定义
TOOLS = [
    {
        "name": "create_support_case",
        "description": "Create a new AWS Support case",
        "target_type": "lambda",
        "target_arn": LAMBDA_ARN
    },
    {
        "name": "describe_support_cases",
        "description": "Query AWS Support cases",
        "target_type": "lambda",
        "target_arn": LAMBDA_ARN
    },
    {
        "name": "add_communication_to_case",
        "description": "Add communication to a support case",
        "target_type": "lambda",
        "target_arn": LAMBDA_ARN
    },
    {
        "name": "resolve_support_case",
        "description": "Resolve a support case",
        "target_type": "lambda",
        "target_arn": LAMBDA_ARN
    },
    {
        "name": "describe_services",
        "description": "Get AWS services list",
        "target_type": "lambda",
        "target_arn": LAMBDA_ARN
    },
    {
        "name": "describe_severity_levels",
        "description": "Get severity levels list",
        "target_type": "lambda",
        "target_arn": LAMBDA_ARN
    },
    {
        "name": "add_attachments_to_set",
        "description": "Upload attachments",
        "target_type": "lambda",
        "target_arn": LAMBDA_ARN
    }
]


def add_lambda_to_gateway():
    """尝试通过 boto3 添加 Lambda 到 Gateway"""

    print("🔧 尝试通过 boto3 配置 AgentCore Gateway...\n")

    # 尝试使用 bedrock-agentcore 客户端
    try:
        client = boto3.client('bedrock-agentcore', region_name=GATEWAY_REGION)
        print("✅ bedrock-agentcore client 创建成功")

        # 尝试获取 Gateway 信息
        try:
            response = client.get_gateway(gatewayIdentifier=GATEWAY_ARN)
            print(f"✅ Gateway 信息获取成功:")
            print(json.dumps(response, indent=2, default=str))
        except Exception as e:
            print(f"⚠️  无法获取 Gateway 信息: {e}")

    except Exception as e:
        print(f"❌ bedrock-agentcore client 不可用: {e}\n")
        print("原因: AWS SDK 可能还未完全支持 AgentCore Gateway API\n")
        return False

    return True


def print_manual_config_guide():
    """打印手动配置指南"""

    print("\n" + "="*70)
    print("📋 手动配置指南 - 通过 AWS Console")
    print("="*70)

    print(f"""
由于 AWS CLI/SDK 暂不完全支持 AgentCore Gateway 配置，
请按照以下步骤在 AWS Console 中手动配置：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

步骤 1: 访问 AgentCore Gateway 控制台
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 登录 AWS Console
2. 切换到 us-west-2 region
3. 访问: Amazon Bedrock → AgentCore → Gateways
4. 找到你的 Gateway: gateway-aws-mcp-fclvp4ujii

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

步骤 2: 添加 Lambda Target
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 点击 Gateway → "Targets" 标签
2. 点击 "Add Target" 按钮
3. 配置 Target:

   Target Type: Lambda Function

   Lambda ARN:
   {LAMBDA_ARN}

   Target Name (可选): aws-support-tools

4. 点击 "Add" 保存

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

步骤 3: 配置 Tool Mappings（重要！）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

在 "Tool Mappings" 部分，逐个添加以下 7 个工具：

工具 1:
  ├─ Tool Name: create_support_case
  ├─ Target: aws-support-tools (刚才添加的Lambda)
  ├─ Description: Create a new AWS Support case
  └─ Payload Mapping: 默认（传递所有参数）

工具 2:
  ├─ Tool Name: describe_support_cases
  ├─ Target: aws-support-tools
  ├─ Description: Query AWS Support cases
  └─ Payload Mapping: 默认

工具 3:
  ├─ Tool Name: add_communication_to_case
  ├─ Target: aws-support-tools
  ├─ Description: Add communication to a support case
  └─ Payload Mapping: 默认

工具 4:
  ├─ Tool Name: resolve_support_case
  ├─ Target: aws-support-tools
  ├─ Description: Resolve a support case
  └─ Payload Mapping: 默认

工具 5:
  ├─ Tool Name: describe_services
  ├─ Target: aws-support-tools
  ├─ Description: Get AWS services list
  └─ Payload Mapping: 默认

工具 6:
  ├─ Tool Name: describe_severity_levels
  ├─ Target: aws-support-tools
  ├─ Description: Get severity levels list
  └─ Payload Mapping: 默认

工具 7:
  ├─ Tool Name: add_attachments_to_set
  ├─ Target: aws-support-tools
  ├─ Description: Upload attachments
  └─ Payload Mapping: 默认

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

步骤 4: 验证配置
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 在 Gateway 页面，确认:
   ✓ Targets 列表中有 aws-support-tools (Lambda)
   ✓ Tool Mappings 列表中有 7 个工具
   ✓ 所有工具都指向同一个 Lambda target

2. 点击 "Save" 或 "Update Gateway" 保存配置

3. 等待 Gateway 状态变为 "Active"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

步骤 5: 测试 Gateway
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

在 Console 中测试一个工具:

1. 选择一个工具，如 "describe_severity_levels"
2. 点击 "Test" 按钮
3. 输入测试 payload:
   {{
     "language": "en"
   }}
4. 点击 "Execute"
5. 应该看到返回的严重级别列表

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

重要提示
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  Lambda 在 us-east-1，Gateway 在 us-west-2
    这是正常的跨 region 调用，已配置好权限

⚠️  所有 7 个工具都指向同一个 Lambda 函数
    Lambda 内部通过 tool_name 参数路由到不同的处理函数

⚠️  Tool Name 必须精确匹配
    Agent 代码中的工具名称必须与 Gateway 中配置的完全一致

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

    print("\n配置完成后，继续执行下一步:")
    print("  cd ../Agent/")
    print("  # 更新 support_case_agent_lambda.py 中的 LAMBDA_ARN")
    print("  # 重新部署 Agent\n")


if __name__ == "__main__":
    success = add_lambda_to_gateway()

    if not success:
        print_manual_config_guide()
