# AWS integration: live DynamoDB proof; agent runtime pending

The DynamoDB persistence adapter has passed a live AWS test. There is no verified live AgentCore endpoint yet; the public demo still uses Render and SQLite.

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
3. Extend the completed DynamoDB persistence proof to the deployed agent workflow.
4. Confirm the caller identity, application bridge and external schedule behavior.
5. Inspect real traces and publish measured latency/cost evidence only after it exists.

Official references:

- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/using-any-agent-framework.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html

## Live persistence proof, September 9, 2026 (UTC)

[Machine-readable result](aws-persistence-evidence.json) from `python3 -m scripts.verify_dynamodb`, executed in AWS CloudShell against `society-relay-hackathon-proof` in `us-east-1`. The existing Store adapter passed create/strongly consistent read, stale conditional-write rejection, mutation retry against a competing update, and a fresh interpreter reading committed state. Two attempts produced counter 11 at version 3. One synthetic record was created; no AI was invoked.

The ACTIVE STANDARD table uses fixed PROVISIONED capacity of 1 read and 1 write unit, within DynamoDB's published 25-unit provisioned free allowance. No other tables existed in this region before creation. No paid compute, extra indexes, streams, backups, or customer-managed encryption were provisioned. CloudShell has no additional service charge. This configuration evidence is not an invoice or an account-wide spending cap.

The console account had no active promotional credits. Bedrock/AgentCore deployment and inference remain pending; no account upgrade was performed. The public application does not use this proof table. Its full AWS route still requires the backend bridge, authentication and external scheduler described above.

- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html
- https://aws.amazon.com/cloudshell/pricing/
- https://aws.amazon.com/free/
