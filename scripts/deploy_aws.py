"""Deploy the isolated Society Relay stack. Run in an authorized AWS CloudShell session."""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
PREFIX = "society-relay-live"
MODEL = "amazon.nova-pro-v1:0"
END = "2026-10-09T00:00:00Z"


def statement(actions, resources):
    return {
        "Effect": "Allow",
        "Action": actions,
        "Resource": resources,
        "Condition": {"DateLessThan": {"aws:CurrentTime": END}},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-account", help="Verified target AWS account ID; required with --apply")
    args = parser.parse_args()
    if not args.apply:
        print(
            json.dumps(
                {
                    "region": REGION,
                    "table": PREFIX,
                    "capacity": "5 read / 5 write units",
                    "roles": [PREFIX + s for s in ["-web", "-dispatch", "-agent", "-schedule"]],
                    "web": "public Lambda Function URL, synthetic cookie-isolated workspaces",
                    "worker": "IAM-only AgentCore + private Lambda dispatcher",
                    "schedule": "EventBridge once per minute",
                    "model": MODEL,
                    "limits": "100 total runs; 150 total model calls; 60KB context; 2500 output tokens",
                    "permissions_expire": END,
                },
                indent=2,
            )
        )
        return
    os.environ["AWS_DEFAULT_REGION"] = REGION
    account = boto3.client("sts").get_caller_identity()["Account"]
    if account != args.expected_account:
        raise RuntimeError("This deployment is restricted to the verified existing AWS account.")
    root = Path(__file__).resolve().parents[1]
    archive = root / "work/society-relay-aws.zip"
    if not archive.is_file():
        raise RuntimeError("Build scripts.package_aws first.")
    table_arn = f"arn:aws:dynamodb:{REGION}:{account}:table/{PREFIX}"
    lambda_arn = f"arn:aws:lambda:{REGION}:{account}:function:{PREFIX}-dispatch"
    bucket = f"{PREFIX}-artifacts-{account}"
    s3 = boto3.client("s3")
    try:
        s3.head_bucket(Bucket=bucket, ExpectedBucketOwner=account)
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in {"404", "NoSuchBucket"}:
            raise
        s3.create_bucket(Bucket=bucket)
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
    s3.upload_file(str(archive), bucket, "deployment.zip", ExtraArgs={"ExpectedBucketOwner": account})
    ddb = boto3.client("dynamodb")
    try:
        ddb.describe_table(TableName=PREFIX)
    except ddb.exceptions.ResourceNotFoundException:
        ddb.create_table(
            TableName=PREFIX,
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PROVISIONED",
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            Tags=[{"Key": "Project", "Value": PREFIX}],
        )
        ddb.get_waiter("table_exists").wait(TableName=PREFIX)
    from relay.store import Store

    store = Store(table=PREFIX)
    try:
        store.read("system-workspaces")
    except KeyError:
        store.create("system-workspaces", {"workspaces": [], "usage": {}, "runs": 0, "lease": None})
    iam = boto3.client("iam")
    logs = statement(
        ["logs:CreateLogStream", "logs:PutLogEvents"],
        [
            f"arn:aws:logs:{REGION}:{account}:log-group:/aws/lambda/{PREFIX}-*:log-stream:*",
            f"arn:aws:logs:{REGION}:{account}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*",
        ],
    )
    table = statement(["dynamodb:GetItem", "dynamodb:PutItem"], table_arn)

    def role(suffix, service, statements):
        name = PREFIX + suffix
        trust = {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": service}, "Action": "sts:AssumeRole"}],
        }
        if service == "bedrock-agentcore.amazonaws.com":
            trust["Statement"][0]["Condition"] = {
                "StringEquals": {"aws:SourceAccount": account},
                "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{REGION}:{account}:*"},
            }
        try:
            result = iam.create_role(
                RoleName=name,
                AssumeRolePolicyDocument=json.dumps(trust),
                Tags=[{"Key": "Project", "Value": PREFIX}],
            )["Role"]
        except iam.exceptions.EntityAlreadyExistsException:
            result = iam.get_role(RoleName=name)["Role"]
            if {t["Key"]: t["Value"] for t in result.get("Tags", [])}.get("Project") != PREFIX:
                raise RuntimeError("Refusing to modify an unowned role")
        iam.put_role_policy(
            RoleName=name,
            PolicyName="SocietyRelayOnly",
            PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": statements}),
        )
        return result["Arn"]

    agent_role = role(
        "-agent",
        "bedrock-agentcore.amazonaws.com",
        [
            table,
            logs,
            statement(
                "logs:CreateLogGroup",
                f"arn:aws:logs:{REGION}:{account}:log-group:/aws/bedrock-agentcore/runtimes/*",
            ),
            statement("s3:GetObject", f"arn:aws:s3:::{bucket}/deployment.zip"),
            statement(
                ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                f"arn:aws:bedrock:{REGION}::foundation-model/{MODEL}",
            ),
        ],
    )
    env = {
        "RELAY_AWS": "1",
        "RELAY_TABLE": PREFIX,
        "RELAY_PUBLIC_DEMO": "1",
        "RELAY_MODEL_PROVIDER": "bedrock",
        "RELAY_MODEL_ID": MODEL,
        "RELAY_AUTO": "0",
        "RELAY_DB": "/tmp/relay.db",
        "RELAY_LIMIT_DB": "/tmp/limits.db",
        "RELAY_DISPATCH_FUNCTION": PREFIX + "-dispatch",
    }
    control = boto3.client("bedrock-agentcore-control")
    name = "society_relay_live"
    existing = [
        r
        for page in control.get_paginator("list_agent_runtimes").paginate()
        for r in page["agentRuntimes"]
        if r["agentRuntimeName"] == name
    ]
    config = {
        "agentRuntimeArtifact": {
            "codeConfiguration": {
                "code": {"s3": {"bucket": bucket, "prefix": "deployment.zip"}},
                "runtime": "PYTHON_3_13",
                "entryPoint": ["aws_main.py"],
            }
        },
        "roleArn": agent_role,
        "networkConfiguration": {"networkMode": "PUBLIC"},
        "environmentVariables": env,
        "lifecycleConfiguration": {"idleRuntimeSessionTimeout": 60, "maxLifetime": 900},
    }
    time.sleep(10)
    if existing:
        runtime_id = existing[0]["agentRuntimeId"]
        control.update_agent_runtime(agentRuntimeId=runtime_id, **config)
    else:
        runtime_id = control.create_agent_runtime(agentRuntimeName=name, **config)["agentRuntimeId"]
    for _ in range(80):
        runtime = control.get_agent_runtime(agentRuntimeId=runtime_id)
        if runtime["status"] == "READY":
            break
        if runtime["status"] in {"CREATE_FAILED", "UPDATE_FAILED"}:
            raise RuntimeError(str(runtime.get("failureReason", runtime["status"])))
        time.sleep(5)
    else:
        raise RuntimeError("Runtime is still provisioning; inspect this runtime before resuming")
    arn = runtime["agentRuntimeArn"]
    env["RELAY_AGENT_ARN"] = arn
    dispatch_role = role(
        "-dispatch",
        "lambda.amazonaws.com",
        [
            table,
            logs,
            statement("lambda:InvokeFunction", lambda_arn),
            statement(
                ["bedrock-agentcore:InvokeAgentRuntime", "bedrock-agentcore:StopRuntimeSession"],
                [arn, arn + "/runtime-endpoint/*"],
            ),
        ],
    )
    web_role = role(
        "-web", "lambda.amazonaws.com", [table, logs, statement("lambda:InvokeFunction", lambda_arn)]
    )
    lam = boto3.client("lambda")
    # New accounts can have fewer than the 100 unreserved executions AWS requires.
    # The DynamoDB lease still serializes agent execution without a quota increase.
    reserve_concurrency = lam.get_account_settings()["AccountLimit"]["UnreservedConcurrentExecutions"] >= 103
    cw = boto3.client("logs")
    time.sleep(10)
    for suffix, handler, role_arn, timeout, concurrency in [
        ("-web", "relay.aws_web.handler", web_role, 30, 2),
        ("-dispatch", "relay.aws_jobs.handler", dispatch_role, 900, 1),
    ]:
        fn = PREFIX + suffix
        try:
            cw.create_log_group(logGroupName="/aws/lambda/" + fn)
        except cw.exceptions.ResourceAlreadyExistsException:
            pass
        cw.put_retention_policy(logGroupName="/aws/lambda/" + fn, retentionInDays=7)
        try:
            existing_function = lam.get_function(FunctionName=fn)
            if existing_function.get("Tags", {}).get("Project") != PREFIX:
                raise RuntimeError("Refusing to modify an unowned function")
        except lam.exceptions.ResourceNotFoundException:
            lam.create_function(
                FunctionName=fn,
                Runtime="python3.13",
                Role=role_arn,
                Handler=handler,
                Code={"S3Bucket": bucket, "S3Key": "deployment.zip"},
                Timeout=timeout,
                MemorySize=512,
                Architectures=["arm64"],
                Environment={"Variables": env},
                Tags={"Project": PREFIX},
            )
            lam.get_waiter("function_active_v2").wait(FunctionName=fn)
        else:
            lam.update_function_code(FunctionName=fn, S3Bucket=bucket, S3Key="deployment.zip")
            lam.get_waiter("function_updated_v2").wait(FunctionName=fn)
            lam.update_function_configuration(
                FunctionName=fn,
                Environment={"Variables": env},
                Timeout=timeout,
                MemorySize=512,
                Role=role_arn,
                Handler=handler,
            )
            lam.get_waiter("function_updated_v2").wait(FunctionName=fn)
        if reserve_concurrency:
            lam.put_function_concurrency(FunctionName=fn, ReservedConcurrentExecutions=concurrency)
    lam.put_function_event_invoke_config(
        FunctionName=PREFIX + "-dispatch", MaximumRetryAttempts=0, MaximumEventAgeInSeconds=60
    )
    try:
        url = lam.create_function_url_config(FunctionName=PREFIX + "-web", AuthType="NONE")["FunctionUrl"]
    except lam.exceptions.ResourceConflictException:
        url = lam.get_function_url_config(FunctionName=PREFIX + "-web")["FunctionUrl"]
    for sid, action, extra in [
        ("PublicFunctionUrl", "lambda:InvokeFunctionUrl", {"FunctionUrlAuthType": "NONE"}),
        ("PublicOnlyViaUrl", "lambda:InvokeFunction", {"InvokedViaFunctionUrl": True}),
    ]:
        try:
            lam.add_permission(
                FunctionName=PREFIX + "-web", StatementId=sid, Action=action, Principal="*", **extra
            )
        except lam.exceptions.ResourceConflictException:
            pass
    scheduler_role = role(
        "-schedule", "scheduler.amazonaws.com", [statement("lambda:InvokeFunction", lambda_arn)]
    )
    scheduler = boto3.client("scheduler")
    scheduling = {
        "Name": PREFIX + "-tick",
        "ScheduleExpression": "rate(1 minute)",
        "State": "ENABLED",
        "EndDate": datetime.fromisoformat(END),
        "FlexibleTimeWindow": {"Mode": "OFF"},
        "Target": {
            "Arn": lambda_arn,
            "RoleArn": scheduler_role,
            "Input": json.dumps({"source": "aws.events"}),
            "RetryPolicy": {"MaximumRetryAttempts": 0, "MaximumEventAgeInSeconds": 60},
        },
    }
    time.sleep(10)
    try:
        scheduler.create_schedule(**scheduling)
    except scheduler.exceptions.ConflictException:
        scheduler.update_schedule(**scheduling)
    receipt = {
        "url": url,
        "agent_runtime_arn": arn,
        "table": PREFIX,
        "region": REGION,
        "model": MODEL,
        "lambda_reserved_concurrency": reserve_concurrency,
        "status": "deployed_not_yet_acceptance_verified",
    }
    (root / "work/aws-deployment.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
