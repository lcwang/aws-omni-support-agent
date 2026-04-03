#!/usr/bin/env python3
"""
创建 DynamoDB 表 - support-agent-feedback-negative

表结构：
- Partition Key: feedback_id (String)
- Sort Key: timestamp (String)
- GSI: issue_category-status-index
"""

import boto3
from botocore.exceptions import ClientError
import sys

# 配置
AWS_REGION = 'us-east-1'
TABLE_NAME = 'support-agent-feedback-negative'
GSI_NAME = 'issue_category-status-index'

def create_feedback_table():
    """创建反馈表"""
    dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)

    table_definition = {
        'TableName': TABLE_NAME,
        'KeySchema': [
            {'AttributeName': 'feedback_id', 'KeyType': 'HASH'},   # Partition key
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}     # Sort key
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'feedback_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'S'},
            {'AttributeName': 'issue_category', 'AttributeType': 'S'},
            {'AttributeName': 'status', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': GSI_NAME,
                'KeySchema': [
                    {'AttributeName': 'issue_category', 'KeyType': 'HASH'},
                    {'AttributeName': 'status', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ],
        'BillingMode': 'PROVISIONED',
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        },
        'Tags': [
            {'Key': 'Project', 'Value': 'AWS-Omni-Support-Agent'},
            {'Key': 'Module', 'Value': 'Feedback-System'},
            {'Key': 'Environment', 'Value': 'Production'}
        ]
    }

    try:
        print(f"Creating DynamoDB table: {TABLE_NAME}...")

        response = dynamodb.create_table(**table_definition)

        print(f"✓ Table creation initiated: {response['TableDescription']['TableName']}")
        print(f"  Status: {response['TableDescription']['TableStatus']}")
        print(f"  ARN: {response['TableDescription']['TableArn']}")

        # 等待表创建完成
        print("\nWaiting for table to become ACTIVE...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=TABLE_NAME)

        # 启用 TTL（可选，90天后自动删除已处理的数据）
        print("\nEnabling TTL...")
        try:
            dynamodb.update_time_to_live(
                TableName=TABLE_NAME,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': 'ttl'  # 需要在写入时设置
                }
            )
            print("✓ TTL enabled (attribute: ttl)")
        except Exception as e:
            print(f"⚠ TTL configuration skipped: {str(e)}")

        print(f"\n✅ Table {TABLE_NAME} created successfully!")
        print(f"\nNext steps:")
        print(f"1. Update backend/config.py with table name: {TABLE_NAME}")
        print(f"2. Ensure Lambda IAM role has DynamoDB permissions")
        print(f"3. Deploy backend API")

        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠ Table {TABLE_NAME} already exists")
            return True
        else:
            print(f"❌ Failed to create table: {e.response['Error']['Message']}")
            return False

    except Exception as e:
        print(f"❌ Failed to create table: {str(e)}")
        return False


def verify_table():
    """验证表是否存在且配置正确"""
    dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)

    try:
        response = dynamodb.describe_table(TableName=TABLE_NAME)
        table = response['Table']

        print(f"\nTable verification:")
        print(f"  Name: {table['TableName']}")
        print(f"  Status: {table['TableStatus']}")
        print(f"  Item Count: {table.get('ItemCount', 0)}")

        # 检查 GSI
        gsi_names = [gsi['IndexName'] for gsi in table.get('GlobalSecondaryIndexes', [])]
        if GSI_NAME in gsi_names:
            print(f"  ✓ GSI '{GSI_NAME}' configured")
        else:
            print(f"  ⚠ GSI '{GSI_NAME}' NOT found")

        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"⚠ Table {TABLE_NAME} does not exist")
            return False
        else:
            print(f"❌ Failed to verify table: {e.response['Error']['Message']}")
            return False


def main():
    """主函数"""
    print("=" * 60)
    print("DynamoDB Table Setup - Feedback System")
    print("=" * 60)

    # 检查表是否已存在
    if verify_table():
        print(f"\n✅ Table {TABLE_NAME} already exists and configured")
        return 0

    # 创建表
    if create_feedback_table():
        # 再次验证
        verify_table()
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
