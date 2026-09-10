## Inspiration

“Any update?” is the unofficial operating system of many apartment societies. One resident reports a problem, another reports the same thing, someone asks for a quote, and everyone keeps asking whether it is done.

Society Relay follows that shared problem through to an outcome. Its defining rule is that a vendor's completion report cannot close an issue. The residents affected must verify restoration.

## What it does

The Good Neighbor demonstration connects two fictional households reporting a water-supply problem in Tower A. It preserves their original reports, proposes a fixed INR 1,800 repair, and finds the access window that works for both households and the vendor while respecting society quiet hours.

Then the demo makes life difficult:

1. A resident changes availability. The only common window disappears, and the old proposal cannot be approved.
   Relay compares alternatives and asks for a one-visit access exception. The resident declines. The agent respects that answer, asks a different household, and obtains consent without editing either household's general availability.
2. The technician reports a delay. Sentinel checks the saved milestone and brings a decision back to the committee without increasing the quote.
3. The facility team reports completion. A resident says the problem is still happening. The issue returns to human attention.
4. After the correction, one household confirms restoration. The issue remains open until the second household confirms too.

Residents, committee members, and facility teams have different actions on one shared incident. Approved plans produce downloadable demonstration work orders and calendar invitations. A committee member can separate a mistaken report match before authorization, and that correction prevents automatic remerging.

## How we built it

A Strands Graph runs Sensemaker, Coordinator, and Sentinel. An evidence specialist assesses reports; an independent model review checks proposed links against the original evidence. When there are no new reports to interpret, a follow-up can enter directly at Sentinel.

The model interprets reports and invokes tools. Deterministic Python rules enforce spending authority, current proposal identifiers, access constraints, human corrections, and resident verification. Versioned workspace writes recheck rules after concurrent changes.

One-time consent is bound to the exact visit date, household group, vendor, quote, and constraints. It can be withdrawn before authorization. A missed or disputed visit needs a fresh planning round; the old yes cannot silently authorize a different date.

The deployed application uses Python, FastAPI, Strands Agents SDK, and an original HTML/CSS/JavaScript interface. A public AWS Lambda Function URL serves the application. A private Lambda dispatcher invokes an IAM-protected AgentCore runtime, which uses Amazon Nova Pro through Bedrock. DynamoDB stores workspaces, conditional version writes, durable job leases, and usage counters. EventBridge Scheduler checks for due work every minute, even when no browser is open.

The live AWS acceptance test verified actual Nova Pro tool calls, duplicate linking, exact-proposal approval, vendor completion, and closure only after both affected households confirmed. The initial agent run took 10.33 seconds. A separate isolated workspace completed through the external scheduler without calling the manual agent endpoint; that test waited 49.11 seconds including the next scheduled tick. The complete resulting states and checks are in docs/aws-live-acceptance.json. An earlier independent DynamoDB proof also verified stale-write rejection, conflict retry, and committed state read by a separate process.

The deployment limits shared usage to 100 workspaces, 100 dispatched jobs, and 150 model calls. These are durable workload controls, not a hard dollar spending cap. The optional local SQLite and Free AI gateway adapters remain available for development.

## Challenges and lessons

The gateway initially stripped native tool-call history fields. The compatibility adapter preserves the conversation as text while leaving actual tool execution to Strands. Early model runs also showed why confident prose is not enough: success must be checked against stored outcomes.

Report similarity is not proof of a common physical cause. Independent review helps, but the product also preserves original evidence and supports durable human corrections. A resident's changing schedule must invalidate stale approval, and a vendor's statement must remain provisional until the affected households agree.

## Try it

[Open the public interactive demo](https://relay.sarthakagrawal.dev/). No login is required. Use fictional information. Workspaces persist in DynamoDB, and an external scheduler resumes due work. Shared AI capacity is limited; failed agent runs preserve completed work for a manual retry. The public video demonstrates the same lifecycle on the earlier hosted build.

## What we verified

The current build passes 50 deterministic tests covering lifecycle authority, stale approvals, concurrency, report separation, missed milestones, false completion, retries, gateway compatibility, and workspace isolation. GitHub Actions runs the checks.

Six targeted live-model cases also passed: duplicate reports, unrelated reports, an embedded instruction attempt, no shared access window, a delayed commitment, and a two-round negotiation after a refusal. Their checks, calls, timings, observed models, and resulting state are committed in `docs/evaluations/`. These are bounded synthetic acceptance results, not a general reliability claim.

A separate hosted acceptance run verified real GPT-OSS-120B inference, report merging, exact-proposal approval, provisional vendor completion, and closure only after both reporting households confirmed. The AI run took 71.28 seconds. An earlier hosted attempt failed at the provider boundary; free inference is not guaranteed. The successful run and resulting state are committed in `docs/hosted-verification.json`.

The video is an edited recording of the working application with synthetic people and vendors. No real communications, bookings, payments, or emergency dispatch occur. The judge-facing role switch is a demonstration tool, not production identity verification.

## What's next

The next operational steps are authenticated resident and staff roles, scoped vendor integrations, reliable external notifications, and a pilot with a consenting society. We have not measured adoption or resident time savings.

## Build disclosure

New application code and original interface assets were created on September 9–10, 2026 with assistance from OpenAI Codex. The existing inference gateway is an external service, not new hackathon work. No existing Fleet or client application code was incorporated. The source is MIT-licensed; dependency licenses remain their own.

[Public source, setup, architecture, and evidence](https://github.com/sarthakagrawal927/society-relay)
