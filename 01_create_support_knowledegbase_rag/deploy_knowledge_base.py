#!/usr/bin/env python3
"""
Knowledge Base 部署脚本 - 从 Jupyter Notebook 提取的自动化版本
创建 S3 bucket、上传文档、创建 Bedrock Knowledge Base、同步数据、存储 KB ID 到 SSM
"""

import os
import sys
import json
import time
import boto3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 切换到脚本所在目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 配置
REGION = 'us-east-1'
os.environ['AWS_DEFAULT_REGION'] = REGION

session = boto3.session.Session(region_name=REGION)
s3_client = session.client('s3')
sts_client = session.client('sts')
ssm_client = session.client('ssm')
bedrock_agent_runtime_client = session.client('bedrock-agent-runtime')

account_id = sts_client.get_caller_identity()['Account']

# 生成唯一后缀
timestamp_str = time.strftime("%Y%m%d%H%M%S", time.localtime())[-7:]
suffix = timestamp_str

# Knowledge Base 配置
KNOWLEDGE_BASE_NAME = "aws-support-qa-knowledge-base"
KNOWLEDGE_BASE_DESCRIPTION = "AWS Support Agent Knowledge Base containing common QA document."
FOUNDATION_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"
DATA_BUCKET_NAME = f"bedrock-aws-support-rag-bucket-{account_id}"
SSM_KB_ID_PARAM = "/support/knowledge_base/kb_id"
DATA_SOURCES = [{"type": "S3", "bucket_name": DATA_BUCKET_NAME}]


def create_s3_bucket(bucket_name):
    """创建 S3 bucket（如果不存在）"""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✓ Bucket {bucket_name} already exists")
        return
    except s3_client.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 403:
            # Bucket exists but not owned by us - name collision
            raise RuntimeError(f"Bucket {bucket_name} exists but is not owned by you. Choose a different name.")
        # 404 means bucket doesn't exist, proceed to create
    except Exception:
        pass

    print(f"  Creating bucket {bucket_name}...")
    s3_client.create_bucket(Bucket=bucket_name)
    print(f"✓ Bucket {bucket_name} created")


def upload_directory(path, bucket_name):
    """上传目录到 S3"""
    for root, dirs, files in os.walk(path):
        for file in files:
            file_to_upload = os.path.join(root, file)
            s3_key = os.path.relpath(file_to_upload, path)
            print(f"  Uploading {file_to_upload} to s3://{bucket_name}/{s3_key}")
            s3_client.upload_file(file_to_upload, bucket_name, s3_key)
    print(f"✓ All files uploaded to {bucket_name}")


def test_knowledge_base(kb_id):
    """测试知识库检索"""
    query = "What are the specifications for EC2 general purpose instances?"
    print(f"\n  Testing KB with query: '{query}'")
    try:
        response = bedrock_agent_runtime_client.retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": kb_id,
                    "modelArn": f"arn:aws:bedrock:{REGION}::foundation-model/{FOUNDATION_MODEL}"
                }
            }
        )
        output = response.get('output', {}).get('text', 'No output')
        print(f"✓ KB test successful. Response preview: {output[:200]}...")
        return True
    except Exception as e:
        print(f"⚠ KB test failed (may need more time for sync): {e}")
        return False


def store_kb_id_to_ssm(kb_id):
    """存储 KB ID 到 SSM Parameter Store"""
    response = ssm_client.put_parameter(
        Name=SSM_KB_ID_PARAM,
        Value=kb_id,
        Type="String",
        Overwrite=True
    )
    print(f"✓ KB ID stored in SSM: {SSM_KB_ID_PARAM} = {kb_id}")
    return response


def main():
    print("\n🚀 Knowledge Base Deployment Script\n")
    print(f"  Region: {REGION}")
    print(f"  Account: {account_id}")
    print(f"  KB Name: {KNOWLEDGE_BASE_NAME}")
    print(f"  S3 Bucket: {DATA_BUCKET_NAME}")
    print()

    # Step 1: 创建 S3 bucket
    print("=" * 60)
    print("[1/5] Creating S3 bucket...")
    create_s3_bucket(DATA_BUCKET_NAME)

    # Step 2: 上传文档
    print("\n" + "=" * 60)
    print("[2/5] Uploading documents to S3...")
    upload_directory("./dataset", DATA_BUCKET_NAME)

    # Step 3: 创建 Knowledge Base（使用 helper 类）
    print("\n" + "=" * 60)
    print("[3/5] Creating Knowledge Base (this takes 3-5 minutes)...")
    print("  This will create: IAM Role, OpenSearch Collection, Vector Index, KB...")

    # 下载最新的 helper（如果需要）
    from utils.knowledge_base import BedrockKnowledgeBase

    knowledge_base = BedrockKnowledgeBase(
        kb_name=KNOWLEDGE_BASE_NAME,
        kb_description=KNOWLEDGE_BASE_DESCRIPTION,
        data_sources=DATA_SOURCES,
        chunking_strategy="SEMANTIC",
        suffix=f'{suffix}-f'
    )

    # Step 4: 同步数据
    print("\n" + "=" * 60)
    print("[4/5] Starting ingestion job (syncing documents)...")
    print("  Waiting 30s for KB to be ready...")
    time.sleep(30)

    knowledge_base.start_ingestion_job()
    kb_id = knowledge_base.get_knowledge_base_id()
    print(f"✓ Knowledge Base ID: {kb_id}")

    # 等待同步完成
    print("  Waiting for ingestion to complete...")
    time.sleep(30)

    # Step 5: 测试并存储
    print("\n" + "=" * 60)
    print("[5/5] Testing and storing KB ID...")
    test_knowledge_base(kb_id)
    store_kb_id_to_ssm(kb_id)

    # 打印摘要
    print("\n" + "=" * 60)
    print("✅ Knowledge Base Deployment Complete!")
    print("=" * 60)
    print(f"  KB ID: {kb_id}")
    print(f"  SSM Parameter: {SSM_KB_ID_PARAM}")
    print(f"  S3 Bucket: {DATA_BUCKET_NAME}")
    print("=" * 60)


if __name__ == '__main__':
    main()
