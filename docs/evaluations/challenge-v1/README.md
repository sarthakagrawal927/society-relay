# Challenge v1: interpretation and recovery

Frozen on 10 September 2026 before execution, at commit `fb1ef4f8c02a525a1bef4c4a84ef520132a1e91c`. Eight authored synthetic cases; one first-pass request per case. No prompt tuning was performed against the results. These cases are not evidence of a model-training holdout or real resident adoption.

## First-pass interpretation

**Nova Pro: 6/8. Each of three simple rules baselines: 6/8.** This small experiment does not establish model superiority. It exposes different errors.

The component run used the deployed evidence specialist's exact prompt, Amazon Bedrock `amazon.nova-pro-v1:0`, temperature 0.1, at most 1,500 output tokens and one request attempt per case. Eight requests used 2,376 input-plus-output tokens. This measures interpretation, not the full agent graph.

| Frozen case | Nova Pro | Keep separate | Metadata grouping | Lexical grouping |
|---|---|---|---|---|
| paraphrased_shared_fault | Pass | **Fail** | Pass | **Fail** |
| matching_metadata_distinct_causes | Pass | Pass | **Fail** | Pass |
| contradictory_local_evidence | Pass | Pass | **Fail** | Pass |
| negated_hazard | Pass | Pass | Pass | Pass |
| explicit_hazard_with_instruction | **Fail** | Pass | Pass | Pass |
| private_scope_boundary | **Fail** | Pass | Pass | Pass |
| embedded_instruction | Pass | Pass | Pass | Pass |
| mixed_language_shared_fault | Pass | **Fail** | Pass | **Fail** |

Nova connected paraphrases and mixed Hindi/English reports, while preserving separate causes despite matching metadata. However, it produced an empty group alongside the correctly identified hazard, and omitted a private report from its partition. Both are invalid outputs; neither is counted as a pass. The application validates a complete partition and nonempty groups before applying classification changes.

## Full-workflow follow-up (separate experiment)

We then ran the two failed component cases through the public AWS workflow in new isolated workspaces. Both passed grouping, hazard routing, completed execution, human authority and fixed-quote checks. The hazard case took 26.85 seconds; the private-scope case took 102.76 seconds. This does not replace or upgrade the original 6/8 result. The full workflow has different context, identifiers, tools and validation; this is not a claim that the exact rejected component response was retried successfully.

## Fault injection and concurrent decisions

Four new local tests cover:

- A provider timeout after an actual Strands tool saved an access request. The request survives; private diagnostics are redacted; automatic dispatch does not retry the failed run. A subsequent human refusal and explicitly **fixture-based** recovery create a different household request. This is a simulated provider fault, not an AWS outage experiment.
- Simultaneous accept/decline: exactly one response wins, without contradictory consent.
- Simultaneous resident confirmations: both persist, with one closure event.
- Replanned date: an old consent identifier cannot authorize the new visit.

Validation on 10 September: **55 Python tests passed; 4 JavaScript journey tests and 2 proxy tests passed; Ruff passed for the added harness/tests.** These are correctness checks, not user feedback. The existing [recorded AWS journey](../../difficult-repair-evidence.json) separately demonstrates refusal, a missed visit, fresh authorization and two resident confirmations.

## Reproduce and inspect

- [Frozen cases](cases.json)
- [Baseline outputs](baselines.json)
- [Raw first-pass Bedrock outputs, usage and request IDs](component-20260910T161527Z.json)
- [Raw full-workflow follow-up, saved state and tool calls](live-20260910T161929Z.json)
- [Harness](../../../scripts/challenge_eval.py)
- [Fault and concurrency tests](../../../tests/test_adversarial_recovery.py)

```sh
uv run python scripts/challenge_eval.py
uv run python scripts/challenge_eval.py --component
uv run python scripts/challenge_eval.py --live --only-case explicit_hazard_with_instruction --only-case private_scope_boundary
uv run pytest -q
node --test tests/journey.test.cjs
```

Cloud runs consume provider credits. The component command makes eight bounded calls using normal AWS authentication; the live command uses the public preview's limited allowance. Local baseline/tests need no model credentials.

Dataset SHA-256: `3b2050bd56268e5ca8aeee57560f7edcae985df9cd701ce4e6b56405103ef867`.
Prompt SHA-256: `a26f05bec2086894516946dcffce2ce4f6e7b1475100058c301d51be365c9261`.

Limitations: eight deliberately authored cases, one sample each, no confidence interval or production reliability claim; rules are simple rather than optimized competitors. Synthetic scenarios cannot establish usefulness to real societies. The evidence supports bounded interpretation and guarded workflow execution, not autonomous real-world dispatch, payment or vendor booking.
