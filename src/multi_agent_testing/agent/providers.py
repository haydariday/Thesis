"""Hosted OpenAI-compatible providers: endpoint checks, key names and extras."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class Provider:
    hostname: str
    api_key_env: str
    # DeepSeek's thinking mode ignores temperature, so the mode must be explicit.
    has_thinking_switch: bool = False
    # Weekday UTC hours [start, end) billed at the peak rate.
    peak_hours_utc: tuple[tuple[int, int], ...] = ()


PROVIDERS = {
    "zen": Provider(hostname="opencode.ai", api_key_env="OPENCODE_API_KEY"),
    "deepseek": Provider(
        hostname="api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        has_thinking_switch=True,
        # https://api-docs.deepseek.com/quick_start/pricing: peak prices are
        # double, Monday to Friday. Chinese public holidays are off-peak but
        # are not modelled, so a run pauses needlessly on those days.
        peak_hours_utc=((1, 4), (6, 10)),
    ),
}

THINKING_MODES = ("enabled", "disabled")


def endpoint_error(backend: str, base_url: str) -> str | None:
    """Why ``base_url`` is not acceptable for ``backend``, or None if it is."""

    provider = PROVIDERS.get(backend)
    if provider is None:
        return None

    endpoint = urlparse(base_url)
    if (
        endpoint.scheme != "https"
        or endpoint.hostname != provider.hostname
        or endpoint.username is not None
        or endpoint.password is not None
        or endpoint.query
        or endpoint.fragment
    ):
        return (
            f"{backend} needs an https://{provider.hostname} base URL "
            "without embedded credentials or query parameters."
        )

    return None


def settings_error(
    backend: str,
    protocol: str,
    temperature: float | None,
    thinking: str | None,
) -> str | None:
    """Check that temperature and thinking settings mean what they say."""

    provider = PROVIDERS.get(backend)
    has_switch = provider is not None and provider.has_thinking_switch

    if thinking is not None and not has_switch:
        return "--thinking applies only to the deepseek backend."

    if has_switch:
        if thinking is None:
            return f"{backend} requires --thinking {{{','.join(THINKING_MODES)}}}."
        if protocol != "chat":
            return f"{backend} supports only --protocol chat."
        if thinking == "enabled" and temperature is not None:
            return (
                "DeepSeek thinking mode ignores temperature; "
                "omit --temperature so the config does not record a value "
                "that had no effect."
            )
        if thinking == "disabled" and temperature is None:
            return "--temperature is required when thinking is disabled."
        return None

    if protocol == "chat" and temperature is None:
        return "--temperature is required with the chat protocol."

    return None


def request_options_error(
    protocol: str, max_tokens: int | None, json_mode: bool
) -> str | None:
    if (max_tokens is not None or json_mode) and protocol != "chat":
        return "--max-tokens and --json-mode need --protocol chat."
    if max_tokens is not None and max_tokens < 1:
        return "--max-tokens must be positive."
    return None


def peak_wait_seconds(
    backend: str,
    now: datetime,
    margin_seconds: float = 0.0,
) -> float:
    """Seconds to wait so that no request falls in a peak-price window.

    Returns 0 when ``now`` is off-peak and no window starts within
    ``margin_seconds``; otherwise the time until that window ends.  ``now``
    must be timezone-aware UTC.
    """

    provider = PROVIDERS.get(backend)
    if provider is None or not provider.peak_hours_utc:
        return 0.0

    margin = timedelta(seconds=margin_seconds)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for day in (midnight - timedelta(days=1), midnight, midnight + timedelta(days=1)):
        if day.weekday() >= 5:
            continue
        for start_hour, end_hour in provider.peak_hours_utc:
            start = day + timedelta(hours=start_hour)
            end = day + timedelta(hours=end_hour)
            if start - margin <= now < end:
                return (end - now).total_seconds()
    return 0.0


def default_api_key_env(backend: str) -> str | None:
    provider = PROVIDERS.get(backend)
    return provider.api_key_env if provider is not None else None


def extra_body(thinking: str | None) -> dict[str, Any] | None:
    """Provider-specific request fields beyond the OpenAI schema."""

    if thinking is None:
        return None
    return {"thinking": {"type": thinking}}
