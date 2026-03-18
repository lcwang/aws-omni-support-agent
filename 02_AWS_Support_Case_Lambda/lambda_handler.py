"""
AWS Support Lambda Handler
将原MCP Server的工具转换为Lambda函数，通过AgentCore Gateway调用
"""

import json
import boto3
import os
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

# 初始化 AWS Support 客户端
support_client = boto3.client('support', region_name='us-east-1')

# Email 验证正则
EMAIL_PATTERN = re.compile(
    r'^(?!.*\.\.)[a-zA-Z0-9](\.?[a-zA-Z0-9_\-+%])*@[a-zA-Z0-9-]+(\.[a-zA-Z]{2,})+$'
)

def validate_emails(email_list: Optional[List[str]]) -> None:
    """验证邮箱地址"""
    if not email_list:
        return
    invalid = [e for e in email_list if not EMAIL_PATTERN.match(e)]
    if invalid:
        raise ValueError(f"Invalid email addresses: {', '.join(invalid)}")


def create_support_case(event: Dict[str, Any]) -> Dict[str, Any]:
    """创建 AWS Support Case"""
    try:
        # 提取参数
        subject = event['subject']
        service_code = event['service_code']
        category_code = event['category_code']
        severity_code = event['severity_code']
        communication_body = event['communication_body']
        cc_emails = event.get('cc_email_addresses')
        language = event.get('language', 'en')
        issue_type = event.get('issue_type', 'technical')
        attachment_set_id = event.get('attachment_set_id')

        # 验证邮箱
        if cc_emails:
            validate_emails(cc_emails)

        # 构建请求参数
        params = {
            'subject': subject,
            'serviceCode': service_code,
            'categoryCode': category_code,
            'severityCode': severity_code,
            'communicationBody': communication_body,
            'language': language,
            'issueType': issue_type
        }

        if cc_emails:
            params['ccEmailAddresses'] = cc_emails
        if attachment_set_id:
            params['attachmentSetId'] = attachment_set_id

        # 调用 AWS Support API
        response = support_client.create_case(**params)

        return {
            'statusCode': 200,
            'body': {
                'caseId': response['caseId'],
                'status': 'success',
                'message': f"Support case created successfully with ID: {response['caseId']}"
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'status': 'error',
                'message': str(e),
                'error_type': type(e).__name__
            }
        }


def describe_support_cases(event: Dict[str, Any]) -> Dict[str, Any]:
    """查询 AWS Support Cases"""
    try:
        params = {
            'includeResolvedCases': event.get('include_resolved_cases', False),
            'includeCommunications': event.get('include_communications', True),
            'language': event.get('language', 'en')
        }

        # 可选参数
        if event.get('case_id_list'):
            params['caseIdList'] = event['case_id_list']
        if event.get('display_id'):
            params['displayId'] = event['display_id']
        if event.get('after_time'):
            params['afterTime'] = event['after_time']
        if event.get('before_time'):
            params['beforeTime'] = event['before_time']
        if event.get('max_results'):
            params['maxResults'] = min(event['max_results'], 100)
        if event.get('next_token'):
            params['nextToken'] = event['next_token']

        response = support_client.describe_cases(**params)

        return {
            'statusCode': 200,
            'body': {
                'cases': response.get('cases', []),
                'nextToken': response.get('nextToken'),
                'status': 'success'
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'status': 'error',
                'message': str(e),
                'error_type': type(e).__name__
            }
        }


def add_communication_to_case(event: Dict[str, Any]) -> Dict[str, Any]:
    """添加回复到 Support Case"""
    try:
        case_id = event['case_id']
        communication_body = event['communication_body']
        cc_emails = event.get('cc_email_addresses')
        attachment_set_id = event.get('attachment_set_id')

        if cc_emails:
            validate_emails(cc_emails)

        params = {
            'caseId': case_id,
            'communicationBody': communication_body
        }

        if cc_emails:
            params['ccEmailAddresses'] = cc_emails
        if attachment_set_id:
            params['attachmentSetId'] = attachment_set_id

        response = support_client.add_communication_to_case(**params)

        return {
            'statusCode': 200,
            'body': {
                'result': response['result'],
                'status': 'success',
                'message': f"Communication added successfully to case: {case_id}"
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'status': 'error',
                'message': str(e),
                'error_type': type(e).__name__
            }
        }


def resolve_support_case(event: Dict[str, Any]) -> Dict[str, Any]:
    """关闭 Support Case"""
    try:
        case_id = event['case_id']
        response = support_client.resolve_case(caseId=case_id)

        return {
            'statusCode': 200,
            'body': {
                'initialCaseStatus': response['initialCaseStatus'],
                'finalCaseStatus': response['finalCaseStatus'],
                'status': 'success',
                'message': f"Support case resolved successfully: {case_id}"
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'status': 'error',
                'message': str(e),
                'error_type': type(e).__name__
            }
        }


def describe_services(event: Dict[str, Any]) -> Dict[str, Any]:
    """获取 AWS 服务列表"""
    try:
        params = {'language': event.get('language', 'en')}

        if event.get('service_code_list'):
            params['serviceCodeList'] = event['service_code_list']

        response = support_client.describe_services(**params)

        # 格式化服务数据
        services = {}
        for service in response.get('services', []):
            services[service['code']] = {
                'name': service['name'],
                'categories': service.get('categories', [])
            }

        return {
            'statusCode': 200,
            'body': {
                'services': services,
                'status': 'success'
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'status': 'error',
                'message': str(e),
                'error_type': type(e).__name__
            }
        }


def describe_severity_levels(event: Dict[str, Any]) -> Dict[str, Any]:
    """获取严重级别列表"""
    try:
        language = event.get('language', 'en')
        response = support_client.describe_severity_levels(language=language)

        # 格式化
        severity_levels = {}
        for level in response.get('severityLevels', []):
            severity_levels[level['code']] = {
                'name': level['name']
            }

        return {
            'statusCode': 200,
            'body': {
                'severity_levels': severity_levels,
                'status': 'success'
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'status': 'error',
                'message': str(e),
                'error_type': type(e).__name__
            }
        }


def add_attachments_to_set(event: Dict[str, Any]) -> Dict[str, Any]:
    """上传附件"""
    try:
        attachments = event['attachments']
        attachment_set_id = event.get('attachment_set_id')

        params = {
            'attachments': [
                {
                    'data': att['data'],
                    'fileName': att['fileName']
                }
                for att in attachments
            ]
        }

        if attachment_set_id:
            params['attachmentSetId'] = attachment_set_id

        response = support_client.add_attachments_to_set(**params)

        return {
            'statusCode': 200,
            'body': {
                'attachmentSetId': response['attachmentSetId'],
                'expiryTime': response['expiryTime'],
                'status': 'success',
                'message': f"Successfully added {len(attachments)} attachment(s)"
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'status': 'error',
                'message': str(e),
                'error_type': type(e).__name__
            }
        }


# 工具路由表
TOOL_HANDLERS = {
    'create_support_case': create_support_case,
    'describe_support_cases': describe_support_cases,
    'add_communication_to_case': add_communication_to_case,
    'resolve_support_case': resolve_support_case,
    'describe_services': describe_services,
    'describe_severity_levels': describe_severity_levels,
    'add_attachments_to_set': add_attachments_to_set
}


def _infer_tool_name(event: Dict[str, Any]) -> Optional[str]:
    """
    根据参数推断工具名称
    这是一个后备方案，当无法从event或环境变量获取tool_name时使用
    """
    # 检查关键参数来推断工具
    if 'subject' in event and 'service_code' in event and 'severity_code' in event:
        return 'create_support_case'

    if 'case_id' in event and 'communication_body' in event:
        return 'add_communication_to_case'

    if 'case_id' in event and len(event) == 1:
        return 'resolve_support_case'

    if 'attachments' in event:
        return 'add_attachments_to_set'

    if 'service_code_list' in event or ('language' in event and len(event) == 1):
        # 可能是 describe_services 或 describe_severity_levels
        # 优先判断为 describe_services
        if 'service_code_list' in event:
            return 'describe_services'
        else:
            # 如果只有 language，默认为 describe_severity_levels
            return 'describe_severity_levels'

    # 如果包含查询相关参数，判断为 describe_support_cases
    if any(key in event for key in ['case_id_list', 'display_id', 'after_time', 'before_time',
                                      'include_resolved_cases', 'include_communications', 'max_results']):
        return 'describe_support_cases'

    # 如果参数为空或只有language，默认为 describe_severity_levels
    if not event or (len(event) == 1 and 'language' in event):
        return 'describe_severity_levels'

    # 无法推断
    return None


def lambda_handler(event, context):
    """
    Lambda 主入口

    支持两种调用格式：

    格式1 (直接调用):
    {
        "tool_name": "create_support_case",
        "parameters": {
            "subject": "...",
            "service_code": "...",
            ...
        }
    }

    格式2 (Gateway调用):
    {
        "subject": "...",
        "service_code": "...",
        ...
    }
    # 工具名从环境变量或context获取
    """
    print(f"[INFO] Received event: {json.dumps(event)}")

    try:
        # 检查是否包含 tool_name（直接调用格式）
        if 'tool_name' in event:
            # 格式1：直接调用
            tool_name = event['tool_name']
            parameters = event.get('parameters', {})
        else:
            # 格式2：Gateway调用，整个event就是parameters
            # 尝试从环境变量或context获取工具名
            tool_name = os.environ.get('TOOL_NAME')

            if not tool_name:
                # 尝试根据参数自动推断工具名称
                tool_name = _infer_tool_name(event)

            parameters = event

        if not tool_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'status': 'error',
                    'message': 'Unable to determine tool_name. Use format: {"tool_name": "xxx", "parameters": {...}} or set TOOL_NAME environment variable'
                })
            }

        # 路由到对应的工具处理器
        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'status': 'error',
                    'message': f'Unknown tool: {tool_name}',
                    'available_tools': list(TOOL_HANDLERS.keys())
                })
            }

        # 执行工具
        result = handler(parameters)

        # 返回结果
        return {
            'statusCode': result['statusCode'],
            'body': json.dumps(result['body'], default=str)
        }

    except Exception as e:
        print(f"[ERROR] Lambda execution error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': f'Lambda execution failed: {str(e)}',
                'error_type': type(e).__name__
            })
        }
