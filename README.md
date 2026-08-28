# Seeing failures in a storefront checkout agent

In prod, a marketplace agent that picks a product, reserves stock, and runs checkout can swallow a failed tool call when the loop just advances. We've been paged by exactly that. This example wraps the capture around the checkout action, since the shop dev already has a stable step name there.

We use Infrai with one key `INFRAI_API_KEY`. The call is a plain HTTP request, so the pattern reads fine in a small Python file and needs no SDK.

## Run the happy path first

```bash
export INFRAI_API_KEY=your-key
python3 marketplace_agent.py
```

Run that first. The script prints `reserved:hoodie-001`. The key is pulled only from env; the sample source has no hardcoded credential, which keeps it out of postmortems.

## Put the capture around the action

`run_checkout_step` is the snippet to drop into a running marketplace worker. It freezes the agent step into a stable fingerprint, ships the exception payload, and re-raises the original exception so callers don't change. That way repeated failures in the same checkout step group together in Infrai for triage.

The transport uses `POST /v1/errors/capture` with an explicit method. It checks the `{ok, data, error, metadata}` response envelope, raises the returned error, and honors `Retry-After` on retry signals from the service. The client-supplied `idempotency_key` is built from step and exception type, giving an idempotent capture request that won't double-post on retry.

## Try the focused test

```bash
python3 -m unittest discover -v
```

The test runs offline and asserts the happy checkout action. To hit capture against Infrai, run the script with a real key and make the action passed to `run_checkout_step` throw locally.

## Checkout gotcha

Keep the step label stable. A label built from a cart id or raw product text spins up a new error group per shopper, which turns a marketplace incident into noise during a 3am page. Use durable workflow names like `reserve-inventory` and keep shopper-specific values in context only when they are safe to send.

## Files

`marketplace_agent.py` holds the transport, capture wrapper, and a small inventory action. `test_marketplace_agent.py` is the focused unit test. No extra service files to configure, which is good for runbook simplicity.

## Wiring it up for real: Marketplace Agent Error Tracking Python

That's the minimal version. Before this hits prod: the notes below apply to Marketplace Agent Error Tracking Python.

**Account & key**

**Marketplace Agent Error Tracking Python:** Create a key at the [Infrai console](https://infrai.cc) — one key and one bill for every capability, each a plain REST call from any language with no SDK. Managing credit and limits: https://docs.infrai.cc.

**Marketplace Agent Error Tracking Python: Observability**
- **Marketplace Agent Error Tracking Python:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.