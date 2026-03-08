import json
from anthropic import Anthropic
from utils.claude_client import get_client, OPUS

SYSTEM = """You are an expert cloud architect assistant with deep knowledge of the analyzed repository.
You have access to tools that give you the full architecture analysis, dependency graph, infrastructure plan,
Kubernetes manifests, Terraform code, and cost estimates.

When answering questions:
- Be precise and reference actual services/components from the analysis
- Use the tools to retrieve relevant data before answering
- Provide actionable insights, not just descriptions
- Keep answers concise and Senior Leadership appropriate"""


def get_tools(state) -> list:
    return [
        {
            "name": "get_service_list",
            "description": "Get the list of all detected services and their architecture pattern",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_dependency_graph",
            "description": "Get the full service dependency map showing which services depend on which",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_infrastructure_plan",
            "description": "Get the planned cloud infrastructure resources",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_modernization_plan",
            "description": "Get the modernization recommendations and migration phases",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_kubernetes_manifests",
            "description": "Get the generated Kubernetes deployment manifests",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_terraform_code",
            "description": "Get the generated Terraform infrastructure code",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_cost_estimation",
            "description": "Get the monthly and annual cost estimation breakdown",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]


def execute_tool(tool_name: str, state) -> str:
    if tool_name == "get_service_list":
        return json.dumps({
            "services": state.detected_services,
            "languages": state.detected_languages,
            "frameworks": state.detected_frameworks,
            "architecture_pattern": state.architecture_pattern,
            "summary": state.repo_summary,
        })
    elif tool_name == "get_dependency_graph":
        return json.dumps(state.service_dependencies)
    elif tool_name == "get_infrastructure_plan":
        return json.dumps(state.infrastructure_plan)
    elif tool_name == "get_modernization_plan":
        return json.dumps(state.modernization_plan)
    elif tool_name == "get_kubernetes_manifests":
        return json.dumps(state.kubernetes_manifests)
    elif tool_name == "get_terraform_code":
        return state.terraform_code[:3000] + "\n...[truncated]" if len(state.terraform_code) > 3000 else state.terraform_code
    elif tool_name == "get_cost_estimation":
        return json.dumps(state.cost_estimation)
    return "{}"


def ask(question: str, state, conversation_history: list) -> tuple[str, list, list]:
    """
    Ask the QA agent a question.
    Returns (answer, updated_history, tool_calls_made)
    """
    client: Anthropic = get_client()
    tools = get_tools(state)

    messages = conversation_history.copy()
    messages.append({"role": "user", "content": question})

    tool_calls_made = []

    while True:
        response = client.messages.create(
            model=OPUS,
            max_tokens=2048,
            system=SYSTEM,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_calls_made.append(tool_name)
                    result = execute_tool(tool_name, state)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Add assistant message with tool use
            messages.append({"role": "assistant", "content": response.content})
            # Add tool results
            messages.append({"role": "user", "content": tool_results})

        else:
            # Final text response
            answer = ""
            for block in response.content:
                if hasattr(block, "text"):
                    answer += block.text

            messages.append({"role": "assistant", "content": answer})
            return answer, messages, tool_calls_made
