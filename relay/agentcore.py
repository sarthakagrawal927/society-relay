"""AgentCore entrypoint. Deploy with IAM auth; invocation IDs are trusted server input only."""

import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from .agent import run_agent
from .store import Store

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    if not os.getenv("RELAY_TABLE"):
        raise RuntimeError("AgentCore requires a durable RELAY_TABLE; local disk is not supported.")
    workspace_id = payload.get("workspace_id")
    incident_ids = payload.get("incident_ids")
    if not isinstance(workspace_id, str) or not isinstance(incident_ids, list) or not incident_ids:
        raise ValueError("workspace_id and nonempty incident_ids are required.")
    return run_agent(Store(), workspace_id, incident_ids, mode="bedrock")


if __name__ == "__main__":
    app.run()
