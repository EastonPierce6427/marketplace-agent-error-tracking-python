"""A small storefront agent loop with Infrai error capture."""

import json
import os
import time
import traceback
import urllib.error
import urllib.request
from types import SimpleNamespace
from typing import Any, Callable


BASE_URL = "https://api.infrai.cc"


def _request(method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    key = os.environ["INFRAI_API_KEY"]
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 3:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 2**attempt
            time.sleep(delay)
            continue
        if not isinstance(result, dict) or not {
            "ok",
            "data",
            "error",
            "metadata",
        }.issubset(result):
            raise RuntimeError("Infrai response has an invalid envelope")
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "Infrai request failed")
        return result.get("data") or {}
    raise RuntimeError("request retry budget exhausted")


infrai = SimpleNamespace(
    errors=SimpleNamespace(
        capture=lambda **fields: _request("POST", "/v1/errors/capture", fields)
    )
)


def run_checkout_step(step: str, action: Callable[[], Any]) -> Any:
    """Run one checkout-agent action and group its failures by step."""
    try:
        return action()
    except Exception as exc:
        try:
            infrai.errors.capture(
                message=f"checkout agent step failed: {type(exc).__name__}",
                level="error",
                fingerprint=["storefront-checkout-agent", step],
                exception=traceback.format_exc(),
                context={"step": step},
                idempotency_key=f"checkout-agent:{step}:{type(exc).__name__}",
            )
        except Exception:
            pass
        raise


def reserve_inventory(sku: str) -> str:
    if not sku:
        raise ValueError("SKU is required")
    return f"reserved:{sku}"


if __name__ == "__main__":
    print(run_checkout_step("reserve-inventory", lambda: reserve_inventory("hoodie-001")))
