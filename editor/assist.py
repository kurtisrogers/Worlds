"""Run one AI assist without writing the chapter."""

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from editor.models import AICall
from editor.openai_provider import OpenAIError, OpenAIProvider, OpenAITimeout
from editor.policy import chapter_prompt, system_instructions

logger = logging.getLogger(__name__)

FAILURE = "The assist failed. The chapter text is unchanged."
AUTHORSHIP = "This is assistance, not authorship."
PROMPT_REJECTION = "The client cannot set the system prompt."
RATE_REJECTION = "A configured per-user rate limit rejected this call."
SPEND_REJECTION = "A configured spend cap rejected this call."
SHARED_REJECTION = "Any shared environment must have both caps before the flag is on."
FLAG_OFF = "AI assist is off."
_MILLION = 1_000_000


@dataclass
class AssistResponse:
    status_code: int
    payload: dict


def get_provider():
    """Build the OpenAI client from environment settings. Tests replace this."""
    return OpenAIProvider(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        timeout=settings.OPENAI_TIMEOUT_SECONDS,
    )


def run_assist(*, user, chapter):
    """Suggest from the stored chapter. Never assign chapter text."""
    if not settings.AI_ASSIST_ENABLED:
        return _rejected(FLAG_OFF, 403)

    if _is_shared() and not _caps_configured():
        return _rejected(SHARED_REJECTION, 403)

    rate = _rate_limit()
    if rate is not None and _calls_in_window(user, rate[1]) >= rate[0]:
        return _rejected(RATE_REJECTION, 429)

    cap = _spend_cap()
    if cap is not None:
        if _prices() is None or _spent(user) >= cap:
            return _rejected(SPEND_REJECTION, 429)

    system = system_instructions()
    user_message = chapter_prompt(chapter)
    call = AICall.objects.create(
        user=user,
        story=chapter.story,
        chapter=chapter,
        model=settings.OPENAI_MODEL,
        provider="openai",
        outcome=AICall.Outcome.PROVIDER_ERROR,
        sent_to_provider=True,
    )
    provider = get_provider()
    try:
        completion = provider.complete(system=system, user=user_message)
    except OpenAITimeout:
        call.outcome = AICall.Outcome.TIMEOUT
        call.save(update_fields=["outcome"])
        _log(call)
        return _failed()
    except OpenAIError:
        _log(call)
        return _failed()
    except Exception:
        _log(call)
        return _failed()

    if not completion.text or not completion.text.strip():
        call.outcome = AICall.Outcome.EMPTY
        call.model = completion.model or call.model
        call.save(update_fields=["outcome", "model"])
        _log(call)
        return _failed()

    call.outcome = AICall.Outcome.SUCCESS
    call.model = completion.model or call.model
    call.input_tokens = completion.input_tokens
    call.output_tokens = completion.output_tokens
    call.cost_cents = _cost_cents(completion, cap)
    call.save(
        update_fields=[
            "outcome",
            "model",
            "input_tokens",
            "output_tokens",
            "cost_cents",
        ]
    )
    _log(call)
    return AssistResponse(
        200,
        {
            "status": "ok",
            "message": AUTHORSHIP,
            "assistance": completion.text,
        },
    )


def _rejected(message, status_code):
    return AssistResponse(status_code, {"status": "rejected", "message": message})


def _failed():
    return AssistResponse(502, {"status": "failed", "message": FAILURE})


def _log(call):
    logger.info(
        "AI call outcome=%s user=%s story=%s chapter=%s model=%s",
        call.outcome,
        call.user_id,
        call.story_id,
        call.chapter_id,
        call.model,
    )


def _is_shared():
    return getattr(settings, "WORLDS_ENVIRONMENT", "shared") != "local"


def _optional(name):
    value = getattr(settings, name, None)
    if value is None or value == "":
        return None
    return value


def _rate_limit():
    limit = _optional("AI_USER_RATE_LIMIT")
    window = _optional("AI_USER_RATE_WINDOW_SECONDS")
    if limit is None or window is None:
        return None
    if limit < 0 or window <= 0:
        return None
    return limit, window


def _spend_cap():
    cap = _optional("AI_SPEND_CAP_CENTS")
    if cap is None or cap < 0:
        return None
    return cap


def _prices():
    incoming = _optional("OPENAI_INPUT_CENTS_PER_MILLION_TOKENS")
    outgoing = _optional("OPENAI_OUTPUT_CENTS_PER_MILLION_TOKENS")
    if incoming is None or outgoing is None:
        return None
    if incoming < 0 or outgoing < 0:
        return None
    return incoming, outgoing


def _caps_configured():
    return _rate_limit() is not None and _spend_cap() is not None


def _calls_in_window(user, window_seconds):
    start = timezone.now() - timedelta(seconds=window_seconds)
    return AICall.objects.filter(
        user=user,
        sent_to_provider=True,
        created_at__gte=start,
    ).count()


def _spent(user):
    query = AICall.objects.filter(user=user)
    window = _optional("AI_SPEND_WINDOW_SECONDS")
    if window is not None and window > 0:
        start = timezone.now() - timedelta(seconds=window)
        query = query.filter(created_at__gte=start)
    total = query.aggregate(total=Sum("cost_cents"))["total"]
    return total or 0


def _cost_cents(completion, cap):
    prices = _prices()
    if cap is not None and not completion.usage_known:
        return cap
    if prices is None:
        return 0
    incoming, outgoing = prices
    numerator = completion.input_tokens * incoming + completion.output_tokens * outgoing
    if numerator <= 0:
        return 0
    return (numerator + _MILLION - 1) // _MILLION
