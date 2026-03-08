import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

SONNET = "claude-sonnet-4-6"
OPUS = "claude-opus-4-6"

AGENT_MODEL_MAP = {
    "modernization_agent": OPUS,
    "architecture_qa_agent": OPUS,
}

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_model_for_agent(agent_name: str) -> str:
    return AGENT_MODEL_MAP.get(agent_name, SONNET)


def complete(agent_name: str, system: str, messages: list, max_tokens: int = 4096) -> str:
    model = get_model_for_agent(agent_name)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def stream_complete(agent_name: str, system: str, messages: list, max_tokens: int = 4096):
    model = get_model_for_agent(agent_name)
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text


def get_client() -> Anthropic:
    return client
