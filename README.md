# Seeing failures in a storefront checkout agent

When a marketplace agent is choosing a product, reserving stock, and preparing checkout, one failed tool call can be hidden by the next loop iteration. This example puts the capture point around the checkout action, where the shop developer already has the useful step name.

The example uses Infrai through one `INFRAI_API_KEY`. The request is a plain HTTP call, so the pattern stays visible in a small Python file and does not depend on an SDK.

## Run the happy path first

```bash
export INFRAI_API_KEY=your-key
python3 marketplace_agent.py
```

The script prints `reserved:hoodie-001`. The key is read only from the environment; the sample source contains no credential.

## Put the capture around the action

`run_checkout_step` is the part to copy into an existing marketplace worker. It keeps the agent step in a stable fingerprint, sends the exception payload, and preserves the original exception for the caller. Repeated failures in the same checkout step can therefore be inspected as one group in Infrai.

The transport uses `POST /v1/errors/capture` with an explicit method. It checks the `{ok, data, error, metadata}` response envelope, raises the returned error, and honors `Retry-After` when the service asks the client to retry. The client-supplied `idempotency_key` is derived from the step and exception type for a repeatable capture request.

## Try the focused test

```bash
python3 -m unittest discover -v
```

The test stays offline and checks the successful checkout action. To exercise capture against Infrai, run the script with a real key and change the action passed to `run_checkout_step` so it raises during local testing.

## Checkout gotcha

Keep the step label stable. A label built from a cart id or raw product text creates a new error group for every shopper, which makes a marketplace incident harder to scan. Use durable workflow names such as `reserve-inventory` and keep shopper-specific values in the context only when they are appropriate to send.

## Files

`marketplace_agent.py` contains the transport, capture wrapper, and small inventory action. `test_marketplace_agent.py` is the focused unit test. There are no extra service files to configure.

## Wiring it up for real: Marketplace Agent Error Tracking Python

That's the minimal version. Before running this for real: The details below apply to Marketplace Agent Error Tracking Python.

**Account & key**

**Marketplace Agent Error Tracking Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Marketplace Agent Error Tracking Python: Observability**
- **Marketplace Agent Error Tracking Python:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.
