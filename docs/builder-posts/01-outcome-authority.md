# Agents for Humans: Why a maintenance agent cannot mark its own work done

A technician writes “fixed.” A resident turns on the tap. Nothing happens.

That disagreement became the central design decision in Society Relay, my Good Neighbor entry for Agents for Humans. A vendor can report completion, but the people affected decide whether the issue is resolved.

The setting is an Indian apartment society. Residents report problems, a committee approves shared spending, and a facility team performs the work. Those people already have messages and task lists. The missing part is following a shared problem through to a verified outcome.

## Three perspectives, one incident

The demonstration starts with two fictional households reporting that Tower A has no water. A Strands graph connects the evidence, prepares a shared visit, and watches the resulting commitment.

The graph has three stages:

- Sensemaker compares reports, with an evidence specialist and an independent model review before a merge.
- Coordinator proposes a vendor and a visit that satisfies the recorded access constraints.
- Sentinel checks saved milestones and brings a missed commitment back to the committee.

The interface gives residents, committee members, and facility staff different actions on the same incident. The demo deliberately allows role switching so a judge can exercise the entire workflow. It is not production authentication.

## Give the model useful work and narrow authority

The agent's tool catalog includes inspecting the workspace, linking reports, negotiating a visit, proposing a vendor, and checking a milestone. It does not include approving spending or confirming that a resident's water supply has returned.

Those transitions live in ordinary backend rules. An approval must reference the current proposal. A quote must fit the ceiling. A feasible access window must still exist. A vendor update moves the incident into verification, not resolution.

This distinction matters even when the model behaves perfectly. Approval is an authority decision; restoration is a statement about a household's experience. Neither becomes the model's decision merely because the model helped coordinate the work.

## A deliberately difficult demo

The recorded walkthrough interrupts the plan three times. First, a household's availability changes and the only shared window disappears. The old proposal cannot be approved. Second, the technician reports a delay. Sentinel checks the milestone and surfaces a committee decision without increasing the quote. Third, a resident challenges the completion report.

After the correction, the first household confirms restoration. The incident remains open. The second household confirms, and only then does the shared incident resolve.

The vendor's statement and the resident's disagreement both remain in the activity record. Neither is rewritten to make the agent appear successful.

## What this proves, and what it does not

The current implementation has 31 passing deterministic tests and five passing targeted live-model cases. Those checks exercise specific boundaries and scenarios; they do not establish reliability across real societies. The demo uses synthetic people and vendors. It sends no real messages, bookings, or payments.

Strands runs the working graph. A Bedrock configuration, DynamoDB adapter, and AgentCore entrypoint are included, but the AWS runtime has not yet been deployed. That distinction is visible in the architecture and README.

The product lesson is simple: an agent can take responsibility for following up without acquiring the authority to declare everyone satisfied.

[Source and setup](https://github.com/sarthakagrawal927/society-relay) · [Lifecycle rules](https://github.com/sarthakagrawal927/society-relay/blob/main/relay/domain.py) · [Strands graph documentation](https://strandsagents.com/docs/user-guide/concepts/multi-agent/graph/)

#AgentsforHumans
