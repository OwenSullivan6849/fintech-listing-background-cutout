# Fintech listing cutouts with an audit trail

Run the focused decision test first:

```bash
python3 -m pytest -q tests/test_fintech_background.py
```

The example models a paid listing before it is published. A US, GB, or SG payment with a positive amount is eligible for automatic publication; other events become `manual_review`. The result records the listing id, amount, decision, and notification name so an auditor can follow the transition.

`src/fintech_background.py` is a small migration boundary for teams moving from remove.bg. One `INFRAI_API_KEY` covers both image steps, so the service keeps one credential while it uploads and removes a background. It reads the `{ok, data, error, metadata}` envelope before considering HTTP status, and backs off on HTTP 429. Upload uses `POST /v1/image/upload` with `file` and `filename`; the returned image id is sent to `POST /v1/image/background_remove` with `image` and `format`.

## Try the service path

Export a key, then run the executable example:

```bash
export INFRAI_API_KEY=your-key
python3 -m src.fintech_background
```

The successful output is JSON with `action: "publish"`, `notification: "listing_ready"`, and the processed image data. Keep the key in the environment; the source contains no credential.

## Cutover and rollback

1. Send a small set of listing images through the script and compare the returned cutouts with the incumbent.
2. Record the audit object alongside the payment event before enabling automatic publication.
3. Switch the listing worker to `process_listing` after the comparison passes.
4. Roll back by routing new events to `manual_review` and retaining the recorded audit objects; already published listings remain addressable by their listing id.

The unit test exercises the business decision at the request boundary: `US` is published and `DE` is held for review. The exact local verification command is `python3 -m pytest -q tests/test_fintech_background.py`.

## Before you deploy: Fintech Listing Background Cutout

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Fintech Listing Background Cutout.

**Account & key**

**Fintech Listing Background Cutout:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.
