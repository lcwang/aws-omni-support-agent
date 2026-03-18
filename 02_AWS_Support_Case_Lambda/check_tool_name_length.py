#!/usr/bin/env python3
"""
检查工具名称长度，确保不超过 64 字符限制
"""

# 你的 Gateway targets
TARGETS = {
    "aws-support-tools": [
        "create_support_case",
        "describe_support_cases",
        "add_communication_to_case",
        "resolve_support_case",
        "describe_services",
        "describe_severity_levels",
        "add_attachments_to_set"
    ],
    "aws-knowledge-base-mcp-server": [
        "aws___get_regional_availability",
        "aws___search_documentation",
        # 添加其他工具...
    ]
}

MAX_LENGTH = 64

print("🔍 检查工具名称长度")
print("="*70)

issues = []

for target_name, tools in TARGETS.items():
    print(f"\nTarget: {target_name}")
    print("-"*70)

    for tool_name in tools:
        # 模拟 Gateway 可能的命名格式
        full_name_format1 = f"target-{target_name}___{tool_name}"
        full_name_format2 = f"{target_name}___{tool_name}"

        length1 = len(full_name_format1)
        length2 = len(full_name_format2)

        # 检查格式1
        status1 = "✅" if length1 <= MAX_LENGTH else "❌"
        print(f"  {status1} {full_name_format1}")
        print(f"     长度: {length1}/64 字符")

        if length1 > MAX_LENGTH:
            issues.append({
                "target": target_name,
                "tool": tool_name,
                "full_name": full_name_format1,
                "length": length1,
                "overflow": length1 - MAX_LENGTH
            })

print("\n")
print("="*70)
print("📊 总结")
print("="*70)

if issues:
    print(f"\n❌ 发现 {len(issues)} 个超长的工具名称:\n")
    for issue in issues:
        print(f"  • {issue['full_name']}")
        print(f"    长度: {issue['length']} (超出 {issue['overflow']} 字符)")
        print(f"    建议:")

        # 建议1: 缩短 target 名称
        short_target = issue['target'][:10]  # 截取前10个字符
        suggested1 = f"target-{short_target}___{issue['tool']}"
        print(f"      1. 缩短 target 名称: {short_target}")
        print(f"         新工具名: {suggested1} ({len(suggested1)} 字符)")

        # 建议2: 直接使用工具名
        suggested2 = issue['tool']
        print(f"      2. 直接使用工具名: {suggested2} ({len(suggested2)} 字符)")
        print()

    print("\n💡 推荐解决方案:")
    print("\n  1. 在 Gateway Console 中重命名 target:")
    for target in set(i['target'] for i in issues):
        short = target[:15] if len(target) > 15 else target
        short = short.replace('-mcp-server', '').replace('aws-', '')
        print(f"     • {target} → {short}")

    print("\n  2. 或在 Tool Mappings 中使用简短的自定义名称")
    print("     （不使用自动生成的 'target-xxx___' 前缀）")

else:
    print("\n✅ 所有工具名称长度都符合要求！")

print("\n" + "="*70)
