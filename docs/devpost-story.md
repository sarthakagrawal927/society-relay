## Inspiration

“Any update?” is the unofficial operating system of many apartment societies. One resident reports a problem, another reports the same thing, someone asks for a quote, and everyone keeps asking whether it is done.

Society Relay follows that shared problem through to an outcome. Its defining rule is that a vendor's completion report cannot close an issue. The residents affected must verify restoration.

## What it does

The Good Neighbor demonstration connects two fictional households reporting a water-supply problem in Tower A. It preserves their original reports, proposes a fixed ₹1,800 repair, and finds the access window that works for both households and the vendor while respecting society quiet hours.

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

The application uses Python, FastAPI, Strands Agents SDK, SQLite, and an original HTML/CSS/JavaScript interface. The tested live inference configuration uses an existing Free AI gateway, with a local adapter that translates model-authored JSON actions into real Strands tool-use events. The evidence view records actual calls and the observed model, not just the requested routing alias.

A Bedrock model option, DynamoDB persistence adapter, and IAM-only AgentCore entrypoint are implemented in the repository. **The AWS cloud runtime is not yet deployed or verified.** The architecture explicitly distinguishes the running application from that deployment path.

## Challenges and lessons

The gateway initially stripped native tool-call history fields. The compatibility adapter preserves the conversation as text while leaving actual tool execution to Strands. Early model runs also showed why confident prose is not enough: success must be checked against stored outcomes.

Report similarity is not proof of a common physical cause. Independent review helps, but the product also preserves original evidence and supports durable human corrections. A resident's changing schedule must invalidate stale approval, and a vendor's statement must remain provisional until the affected households agree.

## What we verified

The current build passes 42 deterministic tests covering lifecycle authority, stale approvals, concurrency, report separation, missed milestones, false completion, retries, gateway compatibility, and workspace isolation. GitHub Actions runs the checks.

Six targeted live-model cases also passed: duplicate reports, unrelated reports, an embedded instruction attempt, no shared access window, a delayed commitment, and a two-round negotiation after a refusal. Their checks, calls, timings, observed models, and resulting state are committed in `docs/evaluations/`. These are bounded synthetic acceptance results, not a general reliability claim.

The video is an edited recording of the working application with synthetic people and vendors. No real communications, bookings, payments, or emergency dispatch occur. The judge-facing role switch is a demonstration tool, not production identity verification.

## What's next

The next operational steps are a verified AWS deployment, authenticated resident and staff roles, a durable external scheduler, scoped vendor integrations, and a pilot with a consenting society. We have not measured adoption or resident time savings.

## Build disclosure

New application code and original interface assets were created on September 9, 2026 with assistance from OpenAI Codex. The existing inference gateway is an external service, not new hackathon work. No existing Fleet or client application code was incorporated. The source is MIT-licensed; dependency licenses remain their own.

[Public source, setup, architecture, and evidence](https://github.com/sarthakagrawal927/society-relay)
