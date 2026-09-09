# Agents for Humans: A shared repair window is a constraint problem

Two households need the same repair. One can provide access in the morning or afternoon; the other can do afternoon or evening. The vendor has several openings, and the society has quiet hours.

The workable plan is the intersection of those constraints. A persuasive explanation cannot create an extra hour of availability.

For Society Relay, my Agents for Humans project, I made this small coordination problem explicit. It gives the agent something useful to arrange and gives the people involved a clear way to change the plan.

## Make the decision inspectable

The synthetic example has these household windows:

| Household | Available windows |
| --- | --- |
| A-304 | 10:00–11:00, 15:00–16:00 |
| A-502 | 15:00–16:00, 17:00–18:00 |

The coordinator evaluates household access, vendor availability, and the society's blocked hours. The UI displays the candidate windows and how many reporting households can attend. In this example, 15:00–16:00 is the common window.

This is a deterministic calculation used by a Strands tool. The model can interpret the reports and explain the proposed plan; it cannot override the calculation by asserting that everyone is available.

## Changes must invalidate consent

A resident can change their availability before authorization. If the shared window disappears, the proposal remains visible but approval becomes unavailable. Restoring a feasible window produces a current proposal that the committee must review.

The backend also checks the proposal identifier at approval time. Hiding a button in the interface would not be enough: another browser could still hold the old proposal. The mutation recomputes the relevant conditions against current state.

## Negotiate without rewriting someone's calendar

Blocking an impossible plan is only the first step. The coordinator can now compare one-time exceptions, including how many households each option would inconvenience. Its Strands tools request consent for a particular date and window. They cannot grant that consent.

In the live two-round test, one household declines. Relay removes alternatives that would approach that household again in the same round, then asks the other household about a different window. Their acceptance makes the shared visit feasible while leaving general availability unchanged. The committee must still approve the current proposal.

The consent is tied to the date, quote, vendor, household group, and availability context. A resident can withdraw it before authorization. If the visit fails, the next plan has a new date and requires fresh consent. An old yes cannot be silently recycled into a new commitment.

Workspace updates use version checks. If another operation wins the write, the losing operation reloads current state and rechecks the rules. That is the boundary that prevents two concurrent approvals from creating duplicate work orders in the tested local implementation.

## Corrections should survive the next agent run

Report matching has a similar problem. Two reports may look related without sharing a cause. An independent model reviewer helps, but it is not proof of physical root cause.

A committee member can separate a mistaken match before work is authorized. That action restores the original report, withdraws the old proposal, and stores a separation rule. The agent is prevented from immediately merging the pair again on its next run.

This turns a human correction into a persistent constraint instead of a message the next model invocation might overlook. The original reports remain available for inspection.

## Where AWS fits

The running local version uses Strands and SQLite. The repository includes a DynamoDB adapter with strongly consistent reads and conditional version writes, plus an AgentCore entrypoint that requires durable storage. A Bedrock model configuration is also available.

Those adapters are implemented but not a verified AWS deployment. The cloud route still needs an application invocation bridge, an external scheduler, restricted runtime permissions, and live validation. The local scheduler's behavior should not be mistaken for an already operating cloud workflow.

I kept that boundary explicit because architecture claims are easy to draw and harder to prove. The useful unit of progress is a plan someone can inspect, change, authorize, and eventually verify.

[Coordination code](https://github.com/sarthakagrawal927/society-relay/blob/main/relay/coordination.py) · [Persistence implementation](https://github.com/sarthakagrawal927/society-relay/blob/main/relay/store.py) · [AWS deployment status](https://github.com/sarthakagrawal927/society-relay/blob/main/docs/aws.md) · [Project source](https://github.com/sarthakagrawal927/society-relay)

#AgentsforHumans
