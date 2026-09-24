"""Small shared OpenRouter JSON client for Talent IQ agents."""

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODEL = "deepseek/deepseek-v4.1-flash"
API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _api_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    key_file = Path(os.environ.get("OPENROUTER_API_KEY_FILE", ROOT / "api.rtf"))
    if not key_file.is_absolute():
        key_file = ROOT / key_file
    if not key_file.exists():
        raise RuntimeError(f"OpenRouter key file not found: {key_file}")
    if key_file.suffix.lower() == ".rtf":
        try:
            result = subprocess.run(
                ["textutil", "-convert", "txt", "-stdout", str(key_file)],
                check=True, capture_output=True, text=True,
            )
            key = result.stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RuntimeError("Could not read the RTF API key file with textutil") from exc
    else:
        key = key_file.read_text(encoding="utf-8")
    key = key.strip()
    if not key:
        raise RuntimeError("OpenRouter key file is empty")
    return key


def json_completion(prompt):
    """Send a prompt to the configured model and parse its JSON response."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:1341",
            "X-Title": "Talent IQ prototype",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"OpenRouter returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not reach OpenRouter: {exc}") from exc
    try:
        return json.loads(response_data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("OpenRouter returned an invalid JSON response") from exc
