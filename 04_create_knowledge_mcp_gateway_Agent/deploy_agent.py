#!/usr/bin/env python3
"""
Agent Runtime 部署脚本 - 使用 direct code deployment（不需要 Docker）
"""
import os
import json
import boto3
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

REGION = "us-east-1"
AGENT_NAME = "AWS_Support_knowledge_QA_Agent"

print("🚀 Deploying Agent to AgentCore Runtime (Code Zip mode, no Docker needed)\n")

from bedrock_agentcore_starter_toolkit import Runtime

runtime = Runtime()

print("[1/3] Configuring runtime...")
response = runtime.configure(
    entrypoint="aws_support_agent.py",
    requirements_file="requirements.txt",
    region=REGION,
    agent_name=AGENT_NAME,
    auto_create_execution_role=True,
    non_interactive=True,
    deployment_type="direct_code_deploy",
    runtime_type="PYTHON_3_13",
)
print(f"✓ Configuration complete")

print("\n[2/3] Launching agent (this takes a few minutes)...")
launch_result = runtime.launch(auto_update_on_conflict=True)
print(f"✓ Launch complete")
print(f"  Agent ARN: {launch_result.agent_arn}")
print(f"  Agent ID: {launch_result.agent_id}")

print("\n[3/3] Waiting for agent to be READY...")
status_response = runtime.status()
status = status_response.endpoint["status"]
end_statuses = ["READY", "CREATE_FAILED", "DELETE_FAILED", "UPDATE_FAILED"]
wait_time = 0
max_wait = 600

while status not in end_statuses and wait_time < max_wait:
    print(f"  Status: {status} ({wait_time}s elapsed)")
    time.sleep(15)
    wait_time += 15
    status_response = runtime.status()
    status = status_response.endpoint["status"]

print(f"\n  Final status: {status}")

if status == "READY":
    print(f"\n✅ Agent deployed successfully!")
    print(f"  Agent ARN: {launch_result.agent_arn}")

    # Save for web client
    import pickle
    with open("../launch_result.pkl", "wb") as f:
        pickle.dump(launch_result, f)
    print(f"  Saved launch_result.pkl for web client")
else:
    print(f"\n❌ Agent deployment failed with status: {status}")
