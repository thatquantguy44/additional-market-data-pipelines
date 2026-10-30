"""Explicit one-off retrieval from the verified official AAII XLS endpoint."""

import os
import ssl
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import certifi

from market_data_pipeline.catalogs.manifest import load_manifest
from market_data_pipeline.data.aaii_xls import selection
from market_data_pipeline.io.bronze import archive, writer_lock
from market_data_pipeline.pipeline import MAX_INPUT_BYTES, promote_capture


def run_live(manifest_path, root, *, start, end, dsn=None):
    manifest = load_manifest(manifest_path)
    if manifest.format != "xls":
        raise ValueError("live AAII runs require the official XLS manifest")
    bounds = selection(start, end)
    if bounds[1] > datetime.now(UTC).date():
        raise ValueError("live date selection cannot end in the future")
    url = manifest.access["source_url"]
    request = Request(
        url,
        headers={"User-Agent": "market-medallion/0.1 (bounded research verification)"},
    )
    with writer_lock(root):
        try:
            context = ssl.create_default_context(
                cafile=os.environ.get("SSL_CERT_FILE") or certifi.where()
            )
            response = urlopen(request, timeout=30, context=context)
        except HTTPError as exc:
            response = exc
        with response:
            payload = response.read(MAX_INPUT_BYTES + 1)
            transport = {
                "transport": "http",
                "source_uri": url,
                "http_status": response.code,
                "http_headers": {
                    key: response.headers[key]
                    for key in ("Content-Type", "Last-Modified", "ETag", "Retry-After")
                    if key in response.headers
                },
            }
        if len(payload) > MAX_INPUT_BYTES:
            raise ValueError("AAII download exceeds 20 MiB limit")
        envelope, directory = archive(
            root,
            payload,
            manifest,
            None,
            datetime.now(UTC),
            transport=transport,
            date_selection={"start": start, "end": end},
        )
        return promote_capture(root, envelope, payload, manifest, directory, dsn)
