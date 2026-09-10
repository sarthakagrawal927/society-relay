# AWS deployment configuration

This plan was implemented on September 10, 2026. See [live acceptance evidence](aws-live-acceptance.json) for the verified public workflow; the configuration below is not itself proof of runtime behavior.

The public FastAPI application runs behind a Lambda Function URL in us-east-1.
It dispatches work to a private Lambda function, which invokes an IAM-protected
AgentCore runtime running Strands and Amazon Nova Pro. DynamoDB persists demo
workspaces, agent leases, and usage counters. EventBridge Scheduler checks for
due work once per minute, including while the browser is closed.

All new resources use the `society-relay-live` prefix, except the AgentCore name
`society_relay_live`. Deployment requires a verified expected account ID.

## Exact access being created

| Role | Allowed access |
| --- | --- |
| society-relay-live-web | Read/write the new DynamoDB table, invoke the private dispatcher, write application logs |
| society-relay-live-dispatch | Read/write that table, invoke the dispatcher and this AgentCore runtime, stop its sessions, write logs |
| society-relay-live-agent | Read the private deployment archive, read/write that table, invoke Nova Pro, create/write runtime logs |
| society-relay-live-schedule | Invoke the private dispatcher |

The web Function URL permits public invocation. Workspaces use random cookies
and synthetic data; the role chooser is a demonstration, not real authentication.
The dispatcher, AgentCore runtime, deployment bucket, and DynamoDB table remain
private. No access keys are created. Data/model permissions expire at
2026-10-09 00:00 UTC; the scheduler also ends then.

## Resource and usage controls

- One private S3 archive bucket and one provisioned DynamoDB table (5 RCU / 5 WCU).
- Two ARM64 Python Lambda functions, each 512 MB; web timeout 30 seconds,
  dispatcher timeout 900 seconds; no provisioned concurrency.
- AgentCore sessions stop after execution, with 60-second idle timeout and
  900-second maximum lifetime.
- At most 100 demo workspaces, 100 dispatched agent jobs, and 150 model calls
  across the deployment. Each model call allows 60 KB of serialized context
  and at most 2,500 output tokens. Limits persist across process restarts.
- A DynamoDB lease permits one agent job at a time. Duplicate deliveries and
  expired jobs cannot begin another execution. Failed runs require manual retry.
- Lambda asynchronous error retries are disabled; Lambda logs retain seven days.
- The account currently permits 50 concurrent Lambda executions, below the
  threshold for reserving per-function concurrency. Deployment uses the existing
  pool; the durable agent lease and inference caps still apply.

These controls bound agent workload, not all AWS charges. Public HTTP requests,
storage and logs can still incur charges. Credit eligibility and remaining
balance must be checked in AWS Billing; the app is not a hard dollar spending cap.

## Deployment and acceptance

Build with `uv run python -m scripts.package_aws`. Review with
`uv run python -m scripts.deploy_aws`. Provision only after approval with
`uv run python -m scripts.deploy_aws --apply --expected-account ACCOUNT_ID`
from the authorized AWS CloudShell session.

Before replacing the submitted demo URL, verify public session isolation,
static assets, a real Nova Pro tool run, human approval and resident-confirmed
closure, persistent state, and scheduler-triggered work. Record the returned
resource IDs and public URL separately from acceptance evidence.
