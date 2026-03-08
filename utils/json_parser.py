import json
import re


def extract_json(raw: str, fallback: dict = None) -> dict:
    """
    Robustly extract a JSON object from a Claude response.
    Tries multiple strategies before returning the fallback.
    """
    if fallback is None:
        fallback = {}

    text = raw.strip()

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip markdown code fences
    fenced = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    fenced = re.sub(r"\s*```$", "", fenced, flags=re.MULTILINE).strip()
    try:
        return json.loads(fenced)
    except json.JSONDecodeError:
        pass

    # Strategy 3: find the outermost { ... } block
    start = text.find("{")
    if start != -1:
        # Walk from end to find matching closing brace
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        # Strategy 4: try sanitizing common issues
                        sanitized = _sanitize(candidate)
                        try:
                            return json.loads(sanitized)
                        except json.JSONDecodeError:
                            break

    return fallback


def _sanitize(s: str) -> str:
    """Fix common JSON issues from LLM output."""
    # Remove trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    # Replace single quotes used as string delimiters (simple cases)
    # Remove comments
    s = re.sub(r"//.*?\n", "\n", s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    return s
