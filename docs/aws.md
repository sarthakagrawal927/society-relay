# AWS integration: implemented adapter, deployment pending

This document distinguishes working local code from cloud infrastructure that has not been deployed. There is no verified live AgentCore endpoint yet.

## Implemented

- `relay/agent.py` selects `BedrockModel` when `RELAY_MODEL_PROVIDER=bedrock`. `RELAY_MODEL_ID` is required rather than assuming access to a particular regional model.
- `relay/agentcore.py` exposes a `BedrockAgentCoreApp` entrypoint. It refuses to run without a DynamoDB table, because ephemeral agent-session disk must not own community state.
- `relay/store.py` uses strongly consistent DynamoDB reads and conditional version writes. A conflicting update retries against current state and rechecks business rules.
- The agent's tools can prepare a quote but cannot invoke the human approval or verification actions.

## Deployment contract

Provision a dedicated DynamoDB table with string partition key `id`. The runtime role should have only `GetItem` and `PutItem` access to that table and the minimum model-invocation and runtime logging permissions. Do not grant table scans to the agent. Scope the application to this table rather than reusing production society data.

Use IAM authentication on the AgentCore endpoint. Only a trusted application backend should submit `workspace_id` and `incident_ids`; never expose this entrypoint as a public unauthenticated API. The public demo's role switch is not a production authorization system.

Set non-secret runtime configuration for `RELAY_TABLE`, `RELAY_MODEL_PROVIDER=bedrock`, `RELAY_MODEL_ID` and the selected AWS region through the hosting platform. Supply AWS permissions through the runtime role, not checked-in access keys.

The deployment requires an application-to-AgentCore invocation bridge and an external scheduled-event mechanism. The current FastAPI application runs the agent locally and its scheduler inventories local SQLite only. Do not simply set a DynamoDB table and assume the complete cloud system is active.

## Cost boundary

The user requested no spending. AWS promotional credits are not evidence of unlimited free usage. Verify account eligibility, credits, region/model availability and the chosen runtime/storage/logging costs before provisioning. A billing alarm is not a hard spending cap.

## Live verification still required

1. Deploy the runtime with restricted permissions and a dedicated test table.
2. Invoke the actual Bedrock model through AgentCore against synthetic cases.
3. Prove durable state across sessions and conditional-write conflict handling against the real table.
4. Confirm the caller identity, application bridge and external schedule behavior.
5. Inspect real traces and publish measured latency/cost evidence only after it exists.

Official references:

- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/using-any-agent-framework.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html
