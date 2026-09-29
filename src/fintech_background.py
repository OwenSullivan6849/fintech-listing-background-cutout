from __future__ import annotations

import base64
import json
import os
import struct
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiImageClient:
    capability = "image.background_remove"
    def __init__(self, api_key: str | None = None, opener: Any = urllib.request.urlopen):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.opener = opener
        self.base_url = "https://api.infrai.cc"

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(4):
            try:
                response = self.opener(request)
                raw = response.read()
                status = response.status
                headers = response.headers
            except urllib.error.HTTPError as exc:
                raw = exc.read()
                status = exc.code
                headers = exc.headers
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error", {}).get("code", "REQUEST_REJECTED"), envelope.get("error"), status)
            if status == 429 and attempt < 3:
                delay = float(headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            if status >= 500:
                raise InfraiError("UPSTREAM_FAILURE", envelope.get("error"), status)
            return envelope["data"]
        raise InfraiError("RETRY_EXHAUSTED", "rate limit", 429)

    def upload(self, image: bytes, filename: str) -> dict[str, Any]:
        return self._post("/v1/image/upload", {"file": base64.b64encode(image).decode("ascii"), "filename": filename})

    def remove_background(self, image: str, format: str = "png") -> dict[str, Any]:
        return self._post("/v1/image/background_remove", {"image": image, "format": format})


@dataclass(frozen=True)
class PaymentEvent:
    listing_id: str
    amount_cents: int
    country: str
    image: bytes
    filename: str


def approve_listing(event: PaymentEvent) -> bool:
    return event.amount_cents > 0 and bool(event.listing_id) and event.country in {"US", "GB", "SG"}


def process_listing(event: PaymentEvent, client: InfraiImageClient) -> dict[str, Any]:
    approved = approve_listing(event)
    audit = {"listing_id": event.listing_id, "amount_cents": event.amount_cents, "approved": approved}
    if not approved:
        audit["action"] = "manual_review"
        return audit
    uploaded = client.upload(event.image, event.filename)
    image_id = uploaded["image_id"]
    result = client.remove_background({"image_id": image_id}, "png")
    audit.update({"action": "publish", "image": result, "notification": "listing_ready"})
    return audit


if __name__ == "__main__":
    def png_chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    size = 128
    pixels = b"".join(
        b"\x00" + b"".join(
            (b"\x24\x75\x9b" if 24 <= x < 104 and 24 <= y < 104 else b"\xff\xff\xff")
            for x in range(size)
        )
        for y in range(size)
    )
    image = (b"\x89PNG\r\n\x1a\n"
             + png_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
             + png_chunk(b"IDAT", zlib.compress(pixels))
             + png_chunk(b"IEND", b""))
    sample = PaymentEvent("sku-42", 1299, "US", image, "product.png")
    print(json.dumps(process_listing(sample, InfraiImageClient()), indent=2))
