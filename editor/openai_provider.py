"""OpenAI chat completions. This is the only model provider."""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIError(Exception):
    """The provider failed. The message never includes prompt or response text."""


class OpenAITimeout(OpenAIError):
    """The provider did not answer in time."""


class OpenAIQuota(OpenAIError):
    """The account is over a quota. The message never includes prompt or response text."""


@dataclass
class Completion:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    usage_known: bool


class OpenAIProvider:
    """Calls OpenAI with a credential supplied by the caller (settings or secrets)."""

    def __init__(self, api_key, model, timeout, opener=None):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._opener = opener or urllib.request.urlopen

    def complete(self, *, system, user):
        if not self.api_key:
            raise OpenAIError("missing credential")
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            _URL,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with self._opener(request, timeout=self.timeout) as response:
                raw = response.read()
        except TimeoutError as exc:
            raise OpenAITimeout("timed out") from exc
        except urllib.error.HTTPError as exc:
            if getattr(exc, "code", None) == 429:
                raise OpenAIQuota("quota") from exc
            raise OpenAIError("request failed") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise OpenAITimeout("timed out") from exc
            raise OpenAIError("request failed") from exc

        return _parse(raw, fallback_model=self.model)


def _parse(raw, *, fallback_model):
    try:
        payload = json.loads(raw.decode("utf-8"))
        text = payload["choices"][0]["message"]["content"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise OpenAIError("request failed") from exc
    model = payload.get("model") or fallback_model
    usage = payload.get("usage")
    if (
        isinstance(usage, dict)
        and "prompt_tokens" in usage
        and "completion_tokens" in usage
    ):
        return Completion(
            text=text or "",
            model=model,
            input_tokens=_token_count(usage["prompt_tokens"]),
            output_tokens=_token_count(usage["completion_tokens"]),
            usage_known=True,
        )
    return Completion(
        text=text or "",
        model=model,
        input_tokens=0,
        output_tokens=0,
        usage_known=False,
    )


def _token_count(value):
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 0
    if count < 0:
        return 0
    return count
