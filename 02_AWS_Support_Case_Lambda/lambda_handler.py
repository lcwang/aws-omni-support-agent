"""
AWS Support Lambda Handler - Zero-Config RBAC (使用 IAM Policy Simulator)
将原MCP Server的工具转换为Lambda函数，通过AgentCore Gateway调用

改造说明：
- 添加了零配置 RBAC：使用 IAM Policy Simulator API 检查用户权限
- 准确处理通配符（*、support:*、support:*Case）、Deny、Condition 等
- QA 工具无需鉴权，Case 写入工具需要鉴权
- 不执行 AssumeRole，不生成临时凭证
- 审计日志记录用户身份
- 权限检查结果缓存 5 分钟，提升性能
"""

import json
import boto3
import os
import re
import time
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

# 初始化 AWS Support 客户端
support_client = boto3.client('support', region_name='us-east-1')

# 初始化 IAM 客户端（用于权限查询）
iam_client = None

# AWS Account ID（用于 Policy Simulator）
_aws_account_id = None

# Email 验证正则
EMAIL_PATTERN = re.compile(
    r'^(?!.*\.\.)[a-zA-Z0-9](\.?[a-zA-Z0-9_\-+%])*@[a-zA-Z0-9-]+(\.[a-zA-Z]{2,})+$'
)

# 工具分类：需要鉴权的工具
CASE_WRITE_TOOLS = {
    'create_support_case',
    'add_communication_to_case',
    'resolve_support_case',
    'add_attachments_to_set'
}

# 工具到权限的映射
TOOL_PERMISSION_MAP = {
    'create_support_case': 'support:CreateCase',
    'add_communication_to_case': 'support:AddCommunicationToCase',
    'resolve_support_case': 'support:ResolveCase',
    'add_attachments_to_set': 'support:AddAttachmentsToSet',
}

# 权限检查缓存（避免重复查询 IAM API）
_permission_cache = {}
CACHE_TTL = 300  # 5 分钟

def validate_emails(email_list: Optional[List[str]]) -> None:
    """验证邮箱地址"""
    if not email_list:
        return
    invalid = [e for e in email_list if not EMAIL_PATTERN.match(e)]
    if invalid:
        raise ValueError(f"Invalid email addresses: {', '.join(invalid)}")


def get_iam_client():
    """获取 IAM 客户端（单例）"""
    global iam_client
    if iam_client is None:
        iam_client = boto3.client('iam')
    return iam_client


def get_account_id():
    """获取 AWS Account ID（单例）"""
    global _aws_account_id
    if _aws_account_id is None:
        sts = boto3.client('sts')
        _aws_account_id = sts.get_caller_identity()['Account']
    return _aws_account_id


# ============================================================================
# 零配置 RBAC - 权限检查逻辑
# ============================================================================

# ============================================================================
# 以下函数已废弃（已改用 IAM Policy Simulator API）
# ============================================================================
#
# 原因：手动解析 IAM Policy 无法正确处理：
#   1. 复杂通配符（如 support:*Case、support:Describe*）
#   2. Deny 语句优先级
#   3. 条件表达式（Condition）
#   4. 资源限制（Resource）
#
# 新实现：使用 simulate_principal_policy API（见 check_user_permission 函数）
# ============================================================================


def check_user_permission(iam_user_name: str, required_action: str) -> bool:
    """
    使用 IAM Policy Simulator 检查用户权限（准确处理通配符、Deny 等）

    Args:
        iam_user_name: IAM User 名称
        required_action: 需要的权限，例如 'support:CreateCase'

    Returns:
        bool: 是否有权限
    """
    # 检查缓存
    cache_key = f"{iam_user_name}:{required_action}:{int(time.time() / CACHE_TTL)}"
    if cache_key in _permission_cache:
        print(f"[RBAC] Using cached permission check for {iam_user_name}:{required_action}")
        return _permission_cache[cache_key]

    print(f"[RBAC] Checking permission for user {iam_user_name}: {required_action}")

    iam = get_iam_client()
    account_id = get_account_id()

    try:
        # 使用 IAM Policy Simulator 检查权限
        response = iam.simulate_principal_policy(
            PolicySourceArn=f'arn:aws:iam::{account_id}:user/{iam_user_name}',
            ActionNames=[required_action],
            ResourceArns=['*']  # Support API 不需要特定资源
        )

        if not response.get('EvaluationResults'):
            print(f"[RBAC] No evaluation results for {iam_user_name}:{required_action}")
            _permission_cache[cache_key] = False
            return False

        result = response['EvaluationResults'][0]
        eval_decision = result.get('EvalDecision', 'denied')

        has_permission = (eval_decision == 'allowed')

        if has_permission:
            print(f"[RBAC] User {iam_user_name} has permission: {required_action}")
        else:
            print(f"[RBAC] User {iam_user_name} does NOT have permission: {required_action} (decision: {eval_decision})")

        # 缓存结果
        _permission_cache[cache_key] = has_permission

        return has_permission

    except iam.exceptions.NoSuchEntityException:
        print(f"[RBAC] IAM user not found: {iam_user_name}")
        _permission_cache[cache_key] = False
        return False
    except Exception as e:
        print(f"[RBAC] Error checking permission: {e}")
        # 安全起见，权限检查失败时拒绝访问
        _permission_cache[cache_key] = False
        return False


def create_support_case(event: Dict[str, Any], iam_user: Optional[str] = None) -> Dict[str, Any]:
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

        # 审计日志（记录用户身份）
        print(f"[AUDIT] Case created by user {iam_user or 'system'}: {response['caseId']} (severity: {severity_code})")

        return {
            'statusCode': 200,
            'body': {
                'caseId': response['caseId'],
                'status': 'success',
                'message': f"Support case created successfully with ID: {response['caseId']}",
                'created_by': iam_user or 'system'
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


def describe_support_cases(event: Dict[str, Any], iam_user: Optional[str] = None) -> Dict[str, Any]:
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


def add_communication_to_case(event: Dict[str, Any], iam_user: Optional[str] = None) -> Dict[str, Any]:
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

        # 审计日志
        print(f"[AUDIT] Communication added by user {iam_user or 'system'} to case {case_id}")

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


def resolve_support_case(event: Dict[str, Any], iam_user: Optional[str] = None) -> Dict[str, Any]:
    """关闭 Support Case"""
    try:
        case_id = event['case_id']
        response = support_client.resolve_case(caseId=case_id)

        # 审计日志
        print(f"[AUDIT] Case resolved by user {iam_user or 'system'}: {case_id}")

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


def describe_services(event: Dict[str, Any], iam_user: Optional[str] = None) -> Dict[str, Any]:
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


def describe_severity_levels(event: Dict[str, Any], iam_user: Optional[str] = None) -> Dict[str, Any]:
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


def add_attachments_to_set(event: Dict[str, Any], iam_user: Optional[str] = None) -> Dict[str, Any]:
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

        # 审计日志
        print(f"[AUDIT] Attachments added by user {iam_user or 'system'}: {len(attachments)} file(s)")

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
    # 排除 _iam_user 参数（这是 RBAC 用的，不是工具参数）
    params = {k: v for k, v in event.items() if k != '_iam_user'}

    # 检查关键参数来推断工具
    if 'subject' in params and 'service_code' in params and 'severity_code' in params:
        return 'create_support_case'

    if 'case_id' in params and 'communication_body' in params:
        return 'add_communication_to_case'

    if 'case_id' in params and len(params) == 1:
        return 'resolve_support_case'

    if 'attachments' in params:
        return 'add_attachments_to_set'

    if 'service_code_list' in params or ('language' in params and len(params) == 1):
        # 可能是 describe_services 或 describe_severity_levels
        # 优先判断为 describe_services
        if 'service_code_list' in params:
            return 'describe_services'
        else:
            # 如果只有 language，默认为 describe_severity_levels
            return 'describe_severity_levels'

    # 如果包含查询相关参数，判断为 describe_support_cases
    if any(key in params for key in ['case_id_list', 'display_id', 'after_time', 'before_time',
                                      'include_resolved_cases', 'include_communications', 'max_results']):
        return 'describe_support_cases'

    # 如果参数为空或只有language，默认为 describe_severity_levels
    if not params or (len(params) == 1 and 'language' in params):
        return 'describe_severity_levels'

    # 无法推断
    return None


def lambda_handler(event, context):
    """
    Lambda 主入口 - 零配置 RBAC 版本

    支持三种调用格式：

    格式1 (直接调用):
    {
        "tool_name": "create_support_case",
        "parameters": {...},
        "_iam_user": "alice"  # 可选，用于权限检查和审计
    }

    格式2 (Gateway调用):
    {
        "subject": "...",
        "service_code": "...",
        ...
    }
    # 工具名从环境变量获取

    格式3 (Gateway调用 with user):
    {
        "subject": "...",
        "_iam_user": "alice"
    }
    """
    print(f"[INFO] Received event: {json.dumps(event, default=str)}")

    try:
        # 提取 IAM User（如果有）
        iam_user = event.get('_iam_user')

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
            # 移除 _iam_user 避免传递给工具函数
            if '_iam_user' in parameters:
                parameters = {k: v for k, v in parameters.items() if k != '_iam_user'}

        if not tool_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'status': 'error',
                    'message': 'Unable to determine tool_name'
                })
            }

        # ============================================================================
        # 核心 RBAC 逻辑：检查用户权限
        # ============================================================================

        if tool_name in CASE_WRITE_TOOLS:
            # Case 写入工具：需要权限检查
            if not iam_user:
                print(f"[RBAC] Authentication required for tool: {tool_name}")
                return {
                    'statusCode': 403,
                    'body': json.dumps({
                        'status': 'error',
                        'message': 'Authentication required for case write operations. Please provide _iam_user parameter.',
                        'error_type': 'AuthenticationRequired'
                    })
                }

            # 检查用户权限
            required_permission = TOOL_PERMISSION_MAP.get(tool_name)
            if required_permission:
                has_permission = check_user_permission(iam_user, required_permission)

                if not has_permission:
                    print(f"[RBAC] User {iam_user} does not have permission: {required_permission}")
                    return {
                        'statusCode': 403,
                        'body': json.dumps({
                            'status': 'error',
                            'message': f'User {iam_user} does not have {required_permission} permission. Please contact your administrator.',
                            'error_type': 'PermissionDenied',
                            'required_permission': required_permission
                        })
                    }

                print(f"[RBAC] User {iam_user} has permission: {required_permission}")

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

        # 执行工具（传递 iam_user 用于审计）
        result = handler(parameters, iam_user)

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
