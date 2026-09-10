"""Bounded Bedrock inference for the credit-funded synthetic deployment."""

import json

from strands.models import BedrockModel

from .aws_jobs import take_persistent


class BoundedBedrockModel(BedrockModel):
    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        encoded = json.dumps([messages, tool_specs, system_prompt, kwargs.get("system_prompt_content")])
        if len(encoded.encode()) > 60000:
            raise ValueError("This workspace exceeds the AWS demonstration's inference context limit.")
        take_persistent("bedrock_model_calls", 150)
        async for event in super().stream(messages, tool_specs, system_prompt, **kwargs):
            yield event
