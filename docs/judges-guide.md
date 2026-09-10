# Society Relay: judge’s guide

**An agent that can hear “no,” recover from a broken promise, and let people decide when the work is done.**

## The people behind the workflow

A-304 needs water restored. A-502 cannot leave work for a revised visit. The committee is responsible for a shared budget. These are fictional households with competing needs, not testimonials. Relay must coordinate a workable repair without treating a resident’s time, consent or money as its own.

[Open the live community desk](https://relay.sarthakagrawal.dev/) and choose **Start the difficult repair** in a fresh demo. The guide labels each human decision and each agent turn. If the shared AI allowance is exhausted, [inspect the recorded AWS run](https://relay.sarthakagrawal.dev/static/repair.html); it is clearly labelled replay evidence.

## Before and after

| Coordination task | With Relay | Authority stays with |
|---|---|---|
| Recognize reports about a shared problem | Model interprets evidence; validated tools connect reports | Committee can separate a mistaken match |
| Compare household and vendor times | Agent uses constraint tools and proposes a fixed-price visit | Residents control access; committee approves the exact proposal |
| Recover after a refusal | Agent considers another household, without changing general availability | The resident may refuse |
| Follow up on a missed visit | Scheduler resumes due work; Sentinel flags the missed promise | Committee requests the next visit; fresh consent is required |
| Decide whether the repair worked | Relay collects separate confirmations | Every reporting household must confirm |

This compares responsibilities. It does not claim measured time savings or real-world adoption.

## What to look for

1. **A refusal changes the plan.** Decline the first one-visit exception. The next request must involve another household. The ₹1,800 quote and general availability remain unchanged.
2. **A missed visit invalidates consent.** Report the delay, then prepare another visit. A new date needs fresh consent and approval.
3. **One confirmation is insufficient.** Confirm A-304 first. The case remains open until A-502 confirms too.
4. **The agent works between human decisions.** AWS EventBridge checks due work every minute, including with the browser closed. The guide triggers eligible work immediately to shorten demonstration waits. Failed runs pause automatic retries.

## Evidence behind the claims

| Question | Inspect |
|---|---|
| What did the live model actually do? | [Five Nova Pro runs and fifteen persisted checkpoints](difficult-repair-evidence.json); live **Activity & evidence** |
| Does work resume outside the browser? | [External scheduler acceptance](aws-live-acceptance.json), including a separate workspace completed without a manual agent request |
| Which AWS services are real? | [Current architecture](architecture.svg), [deployment notes](aws.md) |
| What fails? | [Frozen eight-case challenge and raw failures](evaluations/challenge-v1/README.md): Nova and each rules baseline scored 6/8; no superiority claim |
| What protects human decisions? | [Lifecycle policies](../relay/domain.py), [concurrency and recovery checks](../tests/test_adversarial_recovery.py) |

## Scope

This is a synthetic interactive demonstration. Role switching is not production authentication. Work orders and calendar files are demonstration artifacts; no real vendor booking, message, payment or emergency dispatch occurs. Live workspaces persist in DynamoDB, but shared usage and retention are bounded. No real-user feedback is claimed.
