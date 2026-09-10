# Verified AWS deployment

[Open Society Relay](https://s5yxc4zxd7avumdlujounefyyu0vvpeu.lambda-url.us-east-1.on.aws/)

The AWS stack was deployed and tested on September 10, 2026 in us-east-1.
A Lambda Function URL serves FastAPI. Its private Lambda dispatcher invokes the
IAM-protected `society_relay_live` AgentCore runtime, running Strands with Amazon
Nova Pro. DynamoDB persists workspaces, version checks, job leases, and shared
usage limits. EventBridge Scheduler checks for due work once per minute.

## Live evidence

[Machine-readable acceptance](aws-live-acceptance.json) records actual Nova Pro
calls and persisted states. The first coordination run took 10.33 seconds and
linked two reports into one proposal awaiting human approval. The acceptance
then approved the exact proposal, reported vendor completion, verified that one
household could not close the issue, and confirmed closure after both households
agreed. A fresh visitor received an isolated empty workspace. Its own example
completed through the external scheduler without a manual agent request, in
49.11 seconds including the wait for the next tick.

The [earlier DynamoDB proof](aws-persistence-evidence.json) separately verified
strong reads, stale conditional-write rejection, retries after competing writes,
and committed state read from another process. Its isolated proof table remains
separate from the application's `society-relay-live` table.

These are bounded synthetic acceptance cases, not an uptime or accuracy guarantee.
No real resident data, bookings, payments, or notifications were involved.

## Access and cost controls

The [deployment plan](aws-deployment-plan.md) lists the four scoped roles,
resource configuration, persistent workload limits, and permission expiry.
No AWS access keys are embedded in the application. AgentCore and the dispatcher
are private; only the synthetic web interface is public. The role chooser is
not production authentication.

The account received and redeemed $50 of hackathon credits. The deployment
limits 100 workspaces, 100 jobs, and 150 model calls, serializes agent jobs with a
DynamoDB lease, and stops AgentCore sessions after execution. The scheduler ends
on October 9, 2026, and runtime data/model permissions expire then. Storage,
public web traffic, and logs can still accrue charges: credits and workload
limits are not a hard dollar cap. No final billing measurement is claimed.

## Reproduce

Use `uv run python -m scripts.package_aws` to build the locked ARM64 archive.
Run `uv run python -m scripts.deploy_aws` to inspect the resource plan.
From an authorized AWS environment, provision with
`uv run python -m scripts.deploy_aws --apply --expected-account ACCOUNT_ID`.
The script records resource identifiers and a URL before live acceptance; that
provisioning receipt alone is not evidence of a working agent.

Official deployment reference:
[AgentCore Python code deployment](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html).
