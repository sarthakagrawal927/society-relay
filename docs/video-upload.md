# Video publication package

Status: published September 9, 2026 on the personal YouTube channel of Sarthak Agrawal. YouTube displayed Video published and Checks complete. No issues found.

Public video: https://youtu.be/UXrkD4t4G3Y

Title: **Society Relay — No more “any update?” | Agents for Humans 2026**

Update, September 10: the published description now links the guided live demo and the 15-checkpoint AWS evidence replay. It explicitly dates this recording to September 9 and explains that the closing statement about unverified AWS deployment is superseded by the completed deployment and recorded acceptance evidence. YouTube Studio confirmed the description was saved; visibility remains Public.

Original description package (retained below as recording history, not current deployment status):

Society Relay is a Good Neighbor agent for apartment societies, built with Strands Agents SDK. Two households report one shared problem. Relay connects the evidence, coordinates access, follows up on a missed visit, and keeps the incident open until every reporting household verifies the outcome.

This edited working-app demonstration includes a disappearing access window, a vendor delay, a disputed completion, and final resident verification. People, vendors, work orders, and repairs are synthetic. No real messages, bookings, or payments are sent.

Public MIT source, setup, architecture, and evaluation evidence:
https://github.com/sarthakagrawal927/society-relay

Strands runs the demonstrated agent graph. Bedrock, DynamoDB, and AgentCore adapters are included in the repository; the AWS runtime has not yet been deployed or verified.

Built for the Agents for Humans hackathon, Good Neighbor track. Application code and interface were created with assistance from OpenAI Codex. Narration uses the locally generated Kokoro Heart neural voice. The existing inference gateway is an external service.

Chapters:

00:00 Society Relay / Agents for Humans
00:10 Two reports. One shared problem.
00:26 One fixed quote. A window that works for both homes.
00:42 The common window disappears. Approval is blocked.
00:54 One visit. Explicit consent. No calendar edits.
01:06 A refusal changes the next plan.
01:15 A different household. A workable agreement.
01:26 Exact proposal approval → work order + calendar invite.
01:40 Sentinel follows up. The quote stays fixed.
01:54 The old yes cannot authorize a different date.
02:07 Vendor update ≠ verified outcome.
02:16 The resident says it is still broken.
02:26 A new repair note requires fresh verification.
02:35 A-304 confirms. A-502 still has a say.
02:40 Both households verified the outcome.
02:47 Actual Strands calls. Observed model. Recorded timings.
03:05 Running application and undeployed AWS adapters are distinguished.
03:29 github.com/sarthakagrawal927/society-relay

#AgentsforHumans #StrandsAgents

Local deliverables beside the project directory:

- `society-relay-demo.mp4`: 1920 × 1080 H.264/AAC, approximately 3 minutes 38 seconds.
- `society-relay-demo.srt`: narration-based caption draft with approximate cue timing; review synchronization in the upload preview.

Narration: Kokoro-82M, `af_heart`, speed 0.94, generated locally with kokoro-onnx. This is a synthetic stock voice, not a clone of the entrant or another person. Model: https://huggingface.co/hexgrad/Kokoro-82M (Apache 2.0); inference: https://github.com/thewh1teagle/kokoro-onnx (MIT).

The full rendered narration was transcribed through the existing gateway to check that the main claims were intelligible. This is a transcription check, not human listening feedback.
