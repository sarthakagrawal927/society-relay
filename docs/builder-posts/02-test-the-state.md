# Agents for Humans: Testing what a Strands agent actually changed

“I have prepared the proposal” is not a passing test. A proposal in the database, attached to the correct incident and awaiting the right person's approval, can be.

Building Society Relay for Agents for Humans exposed that difference repeatedly. The product coordinates apartment maintenance using Strands. The development challenge was making model output, tool execution, and stored outcomes agree.

## The transport failure beneath the agent

The free inference gateway available for this project accepted chat requests, but its message schema stripped native tool-call history fields. A request could appear successful while losing information that a normal multi-turn tool conversation depends on.

The fix was a local compatibility adapter. It supplies the tool catalog and conversation history as text, asks the model for a JSON action, and translates that model-authored action into a Strands tool-use event. Strands executes the real tool and supplies its result to the next turn.

The adapter does not generate pretend tool results or replace the agent with a scripted scenario. Invalid arguments still encounter tool validation. The application records the model actually returned by the gateway, because a requested routing alias is not proof of which model ran.

This adapter is specific to the gateway's constraints. A transport that preserves native tool history would not need the same workaround.

## Measure stored outcomes

Some early runs produced confident prose before completing the necessary actions. Instead of treating the final answer as success, the implementation checks the relevant workspace state.

Sensemaker must finish reviewing the reports. Coordinator cannot propose work for an incident that has not been reviewed in that invocation. Each stage has a bounded inference budget. A stage can resume within its limit when required state is still missing; it cannot simply loop indefinitely.

The final run summary comes from stored incident states. The evidence view shows actual tool calls, failures, observed model names, and duration.

## Six small cases with explicit expectations

The repository contains real-model acceptance evidence for six synthetic cases:

- Duplicate water-supply reports should become a shared incident with a proposal.
- Unrelated reports should remain separate.
- An instruction embedded in a report should not acquire approval authority.
- A case without a common access window should not produce an approvable visit.
- A delayed commitment should return to human attention.
- After a resident declines an access exception, a second actual model run must propose a different household. Acceptance must leave general availability unchanged and still require committee approval.

All six saved cases passed in the tested configuration. This is a bounded acceptance set, not a statistical estimate of accuracy. The deterministic suite separately covers stale approvals, concurrent mutations, private-report separation, resident challenges, and other policy boundaries.

The delay path also revealed unnecessary work. Once there are no new reports to understand, running the full graph again wastes inference. The implementation now routes that event directly to Sentinel. The saved delay case completed in 6.75 seconds. Timings vary; this is not a service-level guarantee.

## The evidence should be inspectable

Each saved evaluation contains checks, tool calls, model identity, duration, and resulting state. Reviewers can run the same case scripts with their own supported inference configuration. Provider access and free quotas are external dependencies, so the README distinguishes the tested gateway from optional local and Bedrock routes.

The most useful debugging question was not “Did the agent sound correct?” It was “Which operation happened, what state changed, and which invariant still holds?”

[Evaluation evidence](https://github.com/sarthakagrawal927/society-relay/tree/main/docs/evaluations) · [Gateway adapter](https://github.com/sarthakagrawal927/society-relay/blob/main/relay/gateway.py) · [Strands implementation](https://github.com/sarthakagrawal927/society-relay/blob/main/relay/agent.py) · [Strands hooks](https://strandsagents.com/docs/user-guide/concepts/agents/hooks/)

#AgentsforHumans
