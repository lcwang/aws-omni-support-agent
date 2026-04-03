#!/usr/bin/env python3
"""
Knowledge Base Ingestion 诊断脚本

用于排查为什么 KB 检索不到新添加的文档
"""

import os
import sys
import boto3
import json
from datetime import datetime

# 添加父目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from feedback.config import KNOWLEDGE_BASE_ID, KB_S3_BUCKET, KB_S3_PREFIX, AWS_REGION


def check_environment():
    """检查环境变量配置"""
    print("=" * 60)
    print("📋 环境配置检查")
    print("=" * 60)

    print(f"AWS Region: {AWS_REGION}")
    print(f"Knowledge Base ID: {KNOWLEDGE_BASE_ID or '❌ 未配置'}")
    print(f"S3 Bucket: {KB_S3_BUCKET or '❌ 未配置'}")
    print(f"S3 Prefix: {KB_S3_PREFIX}")
    print()

    if not KNOWLEDGE_BASE_ID or not KB_S3_BUCKET:
        print("❌ Knowledge Base 未配置！请设置环境变量：")
        print("   export KNOWLEDGE_BASE_ID=xxx")
        print("   export KB_S3_BUCKET=xxx")
        return False

    return True


def check_s3_files():
    """检查 S3 中的文件"""
    print("=" * 60)
    print("📁 S3 文件检查")
    print("=" * 60)

    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)

        print(f"Bucket: s3://{KB_S3_BUCKET}/{KB_S3_PREFIX}")
        print()

        response = s3_client.list_objects_v2(
            Bucket=KB_S3_BUCKET,
            Prefix=KB_S3_PREFIX
        )

        if 'Contents' not in response:
            print("❌ 目录为空，没有找到任何文件")
            return False

        files = response['Contents']
        print(f"✅ 找到 {len(files)} 个文件：")
        print()

        for obj in files[:10]:  # 只显示前 10 个
            size_kb = obj['Size'] / 1024
            modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"  • {obj['Key']}")
            print(f"    大小: {size_kb:.2f} KB | 修改时间: {modified}")
            print()

        if len(files) > 10:
            print(f"  ... 还有 {len(files) - 10} 个文件")
            print()

        # 读取最新的文件内容
        latest_file = max(files, key=lambda x: x['LastModified'])
        print(f"📄 最新文件内容预览: {latest_file['Key']}")
        print("-" * 60)

        obj_response = s3_client.get_object(
            Bucket=KB_S3_BUCKET,
            Key=latest_file['Key']
        )
        content = obj_response['Body'].read().decode('utf-8')
        print(content[:500])  # 前 500 字符
        print("-" * 60)
        print()

        return True

    except Exception as e:
        print(f"❌ S3 检查失败: {str(e)}")
        return False


def check_kb_data_source():
    """检查 Knowledge Base 的数据源配置"""
    print("=" * 60)
    print("🗄️  Knowledge Base 数据源检查")
    print("=" * 60)

    try:
        bedrock_agent_client = boto3.client('bedrock-agent', region_name=AWS_REGION)

        # 1. 获取 KB 详情
        kb_response = bedrock_agent_client.get_knowledge_base(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )

        kb = kb_response['knowledgeBase']
        print(f"名称: {kb['name']}")
        print(f"状态: {kb['status']}")
        print(f"创建时间: {kb['createdAt']}")
        print()

        # 2. 获取数据源列表
        ds_response = bedrock_agent_client.list_data_sources(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )

        if not ds_response.get('dataSourceSummaries'):
            print("❌ 没有找到数据源")
            return False, None

        data_sources = ds_response['dataSourceSummaries']
        print(f"✅ 找到 {len(data_sources)} 个数据源：")
        print()

        for ds in data_sources:
            print(f"  数据源 ID: {ds['dataSourceId']}")
            print(f"  名称: {ds['name']}")
            print(f"  状态: {ds['status']}")
            print()

            # 获取详细配置
            ds_detail = bedrock_agent_client.get_data_source(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                dataSourceId=ds['dataSourceId']
            )

            ds_config = ds_detail['dataSource']

            # 检查 S3 配置
            if ds_config['dataSourceConfiguration']['type'] == 'S3':
                s3_config = ds_config['dataSourceConfiguration']['s3Configuration']
                print(f"  S3 Bucket ARN: {s3_config['bucketArn']}")

                # 检查 inclusion prefixes
                if 'inclusionPrefixes' in s3_config:
                    print(f"  ✅ Inclusion Prefixes: {s3_config['inclusionPrefixes']}")

                    # 验证我们的前缀是否匹配
                    if KB_S3_PREFIX in s3_config['inclusionPrefixes']:
                        print(f"  ✅ 前缀匹配！Data Source 会 ingest {KB_S3_PREFIX} 下的文件")
                    else:
                        print(f"  ⚠️  前缀不匹配！")
                        print(f"     代码使用: {KB_S3_PREFIX}")
                        print(f"     Data Source 配置: {s3_config['inclusionPrefixes']}")
                else:
                    print(f"  ℹ️  没有配置 inclusion prefixes（会 ingest 整个 bucket）")

                print()

        return True, data_sources[0]['dataSourceId']

    except Exception as e:
        print(f"❌ Knowledge Base 检查失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None


def check_ingestion_jobs(data_source_id):
    """检查 Ingestion Job 状态"""
    print("=" * 60)
    print("🔄 Ingestion Job 状态检查")
    print("=" * 60)

    try:
        bedrock_agent_client = boto3.client('bedrock-agent', region_name=AWS_REGION)

        response = bedrock_agent_client.list_ingestion_jobs(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=data_source_id,
            maxResults=10
        )

        jobs = response.get('ingestionJobSummaries', [])

        if not jobs:
            print("❌ 没有找到任何 ingestion job")
            print("   可能原因：从未触发过同步")
            return False

        print(f"✅ 找到 {len(jobs)} 个 ingestion job（最近 10 个）：")
        print()

        for job in jobs:
            job_id = job['ingestionJobId']
            status = job['status']
            started = job['startedAt'].strftime('%Y-%m-%d %H:%M:%S')

            # 状态图标
            if status == 'COMPLETE':
                icon = "✅"
            elif status == 'IN_PROGRESS':
                icon = "🔄"
            elif status == 'FAILED':
                icon = "❌"
            else:
                icon = "⚠️"

            print(f"  {icon} Job ID: {job_id}")
            print(f"     状态: {status}")
            print(f"     开始时间: {started}")

            if 'statistics' in job:
                stats = job['statistics']
                print(f"     统计: {stats}")

            print()

        # 检查最新 job
        latest_job = jobs[0]

        if latest_job['status'] == 'IN_PROGRESS':
            print("⏳ 最新的 job 正在进行中，请等待完成...")
            return True
        elif latest_job['status'] == 'COMPLETE':
            print("✅ 最新的 job 已完成，文档应该可以检索")
            return True
        elif latest_job['status'] == 'FAILED':
            print("❌ 最新的 job 失败了！需要查看错误日志")

            # 获取详细错误
            detail = bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                dataSourceId=data_source_id,
                ingestionJobId=latest_job['ingestionJobId']
            )

            if 'failureReasons' in detail['ingestionJob']:
                print("   失败原因:")
                for reason in detail['ingestionJob']['failureReasons']:
                    print(f"     • {reason}")

            return False

        return True

    except Exception as e:
        print(f"❌ Ingestion Job 检查失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_kb_retrieval(test_query=None):
    """测试 Knowledge Base 检索"""
    print("=" * 60)
    print("🔍 Knowledge Base 检索测试")
    print("=" * 60)

    if not test_query:
        test_query = input("输入测试问题（直接回车跳过）: ").strip()
        if not test_query:
            print("跳过检索测试")
            return

    try:
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)

        print(f"查询: {test_query}")
        print()

        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': test_query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 5
                }
            }
        )

        results = response.get('retrievalResults', [])

        if not results:
            print("❌ 没有找到任何结果")
            print("   可能原因：")
            print("   1. Ingestion job 还没完成")
            print("   2. 文档内容与查询相似度太低")
            print("   3. Data Source 配置的前缀不对")
            return

        print(f"✅ 找到 {len(results)} 个结果：")
        print()

        for idx, result in enumerate(results, 1):
            content = result['content']['text']
            score = result['score']

            print(f"  结果 {idx} (相似度: {score:.4f}):")
            print(f"  {'-' * 56}")
            print(f"  {content[:300]}...")
            print()

    except Exception as e:
        print(f"❌ 检索测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


def trigger_new_ingestion(data_source_id):
    """手动触发新的 ingestion job"""
    print()
    choice = input("是否手动触发新的 ingestion job？(y/n): ").strip().lower()

    if choice != 'y':
        print("跳过")
        return

    try:
        bedrock_agent_client = boto3.client('bedrock-agent', region_name=AWS_REGION)

        response = bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=data_source_id
        )

        job_id = response['ingestionJob']['ingestionJobId']
        print(f"✅ 已触发新的 ingestion job: {job_id}")
        print("   请等待几分钟后再测试检索")

    except Exception as e:
        print(f"❌ 触发失败: {str(e)}")


def main():
    """主函数"""
    print()
    print("🔬 Knowledge Base Ingestion 诊断工具")
    print()

    # 1. 检查环境配置
    if not check_environment():
        return

    # 2. 检查 S3 文件
    check_s3_files()

    # 3. 检查 KB 数据源
    success, data_source_id = check_kb_data_source()
    if not success:
        return

    # 4. 检查 Ingestion Jobs
    check_ingestion_jobs(data_source_id)

    # 5. 测试检索
    test_kb_retrieval()

    # 6. 可选：触发新 ingestion
    trigger_new_ingestion(data_source_id)

    print()
    print("=" * 60)
    print("✅ 诊断完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
