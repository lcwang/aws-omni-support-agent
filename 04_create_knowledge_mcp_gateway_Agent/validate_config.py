#!/usr/bin/env python3
"""
配置验证脚本
用于检查 agentic_rag_mcp.py 的配置是否正确

Usage:
    python validate_config.py
"""

import sys
import os


def check_environment():
    """检查环境配置"""
    print("=" * 60)
    print("🔍 环境配置检查")
    print("=" * 60)

    # 检查 region 配置
    region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
    if region:
        print(f"✅ AWS_REGION: {region}")
    else:
        print("⚠️  未设置 AWS_REGION，将自动检测")

    # 检查其他配置
    configs = {
        'SSM_GATEWAY_PARAM': '/support/agentgateway/aws_support_gateway',
        'SSM_KB_PARAM': '/support/knowledge_base/kb_id',
        'BEDROCK_MODEL_ID': 'global.anthropic.claude-opus-4-5-20251101-v1:0',
        'MODEL_TEMPERATURE': '0.3',
        'SSM_TIMEOUT': '10',
        'MCP_TIMEOUT': '30',
        'MAX_RETRIES': '3',
    }

    for key, default in configs.items():
        value = os.environ.get(key, default)
        is_default = key not in os.environ
        status = "📌 (默认)" if is_default else "✅ (自定义)"
        print(f"{status} {key}: {value}")

    print()


def check_aws_credentials():
    """检查 AWS 凭证"""
    print("=" * 60)
    print("🔑 AWS 凭证检查")
    print("=" * 60)

    try:
        import boto3
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ Account: {identity['Account']}")
        print(f"✅ User/Role: {identity['Arn']}")
    except Exception as e:
        print(f"❌ 无法获取 AWS 凭证: {e}")
        print("   请运行: aws configure")
        return False

    print()
    return True


def check_region_detection():
    """测试 region 自动检测"""
    print("=" * 60)
    print("🌍 Region 自动检测测试")
    print("=" * 60)

    try:
        # 临时导入以测试
        sys.path.insert(0, os.path.dirname(__file__))
        from agentic_rag_mcp import get_aws_region

        detected_region = get_aws_region()
        print(f"✅ 检测到的 Region: {detected_region}")

    except ImportError as e:
        print(f"⚠️  无法导入模块（可能缺少依赖）: {e}")
    except Exception as e:
        print(f"❌ Region 检测失败: {e}")
        return False

    print()
    return True


def check_ssm_parameters():
    """检查 SSM 参数是否存在"""
    print("=" * 60)
    print("📦 SSM 参数检查")
    print("=" * 60)

    try:
        import boto3
        from agentic_rag_mcp import REGION, SSM_Gateway_Name, SSM_Knowledge_Base

        ssm = boto3.client('ssm', region_name=REGION)

        # 检查 Gateway 参数
        try:
            response = ssm.get_parameter(Name=SSM_Gateway_Name)
            gateway_url = response['Parameter']['Value']
            print(f"✅ Gateway URL: {gateway_url[:50]}...")
        except Exception as e:
            print(f"❌ Gateway 参数不存在: {SSM_Gateway_Name}")
            print(f"   错误: {e}")

        # 检查 Knowledge Base 参数
        try:
            response = ssm.get_parameter(Name=SSM_Knowledge_Base)
            kb_id = response['Parameter']['Value']
            print(f"✅ Knowledge Base ID: {kb_id}")
        except Exception as e:
            print(f"❌ Knowledge Base 参数不存在: {SSM_Knowledge_Base}")
            print(f"   错误: {e}")

    except ImportError:
        print("⚠️  无法导入 boto3 或配置模块")
    except Exception as e:
        print(f"❌ SSM 检查失败: {e}")
        return False

    print()
    return True


def check_dependencies():
    """检查依赖包"""
    print("=" * 60)
    print("📚 依赖包检查")
    print("=" * 60)

    required_packages = [
        'boto3',
        'bedrock_agentcore',
        'strands',
        'strands_tools',
    ]

    all_ok = True
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (未安装)")
            all_ok = False

    if not all_ok:
        print("\n安装缺失的依赖:")
        print("  uv pip install -r requirements.txt")

    print()
    return all_ok


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 agentic_rag_mcp.py 配置验证工具")
    print("=" * 60)
    print()

    results = []

    # 1. 环境配置
    check_environment()

    # 2. AWS 凭证
    results.append(("AWS 凭证", check_aws_credentials()))

    # 3. 依赖包
    results.append(("依赖包", check_dependencies()))

    # 4. Region 检测
    results.append(("Region 检测", check_region_detection()))

    # 5. SSM 参数
    results.append(("SSM 参数", check_ssm_parameters()))

    # 总结
    print("=" * 60)
    print("📊 验证总结")
    print("=" * 60)

    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
        if not result:
            all_passed = False

    print()

    if all_passed:
        print("🎉 所有检查通过！可以开始使用 agentic_rag_mcp.py")
        return 0
    else:
        print("⚠️  部分检查失败，请修复后再试")
        return 1


if __name__ == "__main__":
    sys.exit(main())
