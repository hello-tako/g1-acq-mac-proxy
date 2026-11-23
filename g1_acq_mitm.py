# -*- coding: utf-8 -*-
"""
g1_acq_mitm.py — Free macOS/Linux MITM Proxy Addon for Google One (iOS) Promo SKU Mapping.

Equivalent to the Shadowrocket `g1-acq.js` (v6) script, designed to run on a Mac or PC
via `mitmproxy` / `mitmdump` so an iPhone or iPad on the same Wi-Fi LAN can trigger
Google AI Ultra (20TB / 30TB) promotional introductory SKUs (90% off / 75% off for 3 months)
via Apple App Store In-App Purchase without purchasing Shadowrocket.

Key Features:
1. 1-Click iOS CA Certificate Onboarding:
   Visiting `http://<HOST_LAN_IP>:8888`, `http://cert.local`, or `http://mitm.it` in iOS Safari
   directly serves `~/.mitmproxy/mitmproxy-ca-cert.pem` with `application/x-x509-ca-cert`,
   avoiding iOS Safari's automatic HTTPS upgrade issue on `mitm.it`.
2. QUIC / HTTP/3 Downgrade Protection:
   Strips `Alt-Svc` headers from `one.google.com` responses so the iOS Google App stays on
   HTTP/2 or HTTP/1.1 through the HTTP proxy instead of bypassing inspection via UDP 443 QUIC.
3. Catalog-Aware SKU Rewriting:
   Scans `https://one.google.com/ai?...` responses for available `.acq` promotional SKUs,
   maps standard iOS monthly SKUs (`g1.ios.20tb.m.v2`, `g1.ios.30tb.ai.pro.m`) to 90%-off
   introductory SKUs (`g1.20tb.3months_ip_90p.acq`, `g1.ai.ultra.3months_ip_90p.acq`), and
   automatically falls back to 75%-off SKUs (`75p.acq`) if 90p is absent from the catalog.
"""
import os
import re
from pathlib import Path
from mitmproxy import http

# Original iOS monthly In-App Purchase SKU -> Primary 90%-off (3 months) promotional SKU
SKU_MAP = {
    "g1.ios.20tb.m.v2": "g1.20tb.3months_ip_90p.acq",
    "g1.ios.30tb.ai.pro.m": "g1.ai.ultra.3months_ip_90p.acq",
}

# Fallback 75%-off (3 months) promotional SKU when 90p is not present in the catalog
FALLBACK = {
    "g1.20tb.3months_ip_90p.acq": "g1.20tb.3months_ip_75p.acq",
    "g1.ai.ultra.3months_ip_90p.acq": "g1.ai.ultra.3months_ip_75p.acq",
}

ACQ_REGEX = re.compile(r"g1\.[a-z0-9._]{2,60}acq")
ALL_SKU_REGEX = re.compile(r"g1\.[a-z0-9._]{2,60}")
CERT_PATH = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"
HOST_IP = os.environ.get("G1_HOST_IP", "")
STRICT_CATALOG = os.environ.get("G1_STRICT_CATALOG", "0") == "1"


def request(flow: http.HTTPFlow) -> None:
    host = flow.request.pretty_host
    onboarding_hosts = {"mitm.it", "cert.local", "127.0.0.1", "localhost"}
    if HOST_IP:
        onboarding_hosts.add(HOST_IP)

    # Serve the mitmproxy Root CA certificate directly over plain HTTP for 1-click iOS install
    if (host in onboarding_hosts or host.startswith("192.168.") or host.startswith("10.") or host.startswith("172.")) and CERT_PATH.exists():
        flow.response = http.Response.make(
            200,
            CERT_PATH.read_bytes(),
            {
                "Content-Type": "application/x-x509-ca-cert",
                "Content-Disposition": 'inline; filename="mitmproxy-ca-cert.pem"',
                "Cache-Control": "no-store",
            },
        )
        print(
            f"[g1-acq] Served mitmproxy CA certificate profile directly to iOS client ({flow.client_conn.peername})",
            flush=True,
        )


def response(flow: http.HTTPFlow) -> None:
    host = flow.request.pretty_host
    if host != "one.google.com":
        return

    # Strip Alt-Svc so iOS Google App does not upgrade to QUIC (UDP 443) and bypass the HTTP proxy
    for hdr in ("alt-svc", "Alt-Svc"):
        if hdr in flow.response.headers:
            del flow.response.headers[hdr]

    path = flow.request.path
    content_type = flow.response.headers.get("content-type", "")
    if not (
        path.startswith("/ai")
        or "text/" in content_type
        or "json" in content_type
        or "javascript" in content_type
    ):
        return

    body = flow.response.get_text(strict=False)
    if not body:
        return

    has_target = any(k in body for k in SKU_MAP)
    if not has_target and not path.startswith("/ai"):
        return

    catalog = list(dict.fromkeys(ACQ_REGEX.findall(body)))
    all_skus = list(dict.fromkeys(ALL_SKU_REGEX.findall(body)))

    print(f"\n[g1-acq] Intercepted response: https://{host}{path[:90]}", flush=True)
    print(f"[g1-acq] All g1.* SKUs in response: {', '.join(all_skus) if all_skus else 'NONE'}", flush=True)
    print(
        f"[g1-acq] Promotional (.acq) SKUs in account catalog: {', '.join(catalog) if catalog else 'NONE'}",
        flush=True,
    )

    if STRICT_CATALOG and not catalog:
        print(
            "[g1-acq] G1_STRICT_CATALOG=1 is enabled and no .acq SKUs exist in this account's catalog; skipping rewrite so standard plans remain visible.",
            flush=True,
        )
        return

    out = body
    total = 0
    for src_sku, target_sku in SKU_MAP.items():
        count = out.count(src_sku)
        if count == 0:
            continue

        chosen_sku = target_sku
        if chosen_sku not in catalog and FALLBACK.get(chosen_sku) in catalog:
            fb = FALLBACK[chosen_sku]
            print(
                f"[g1-acq] Primary SKU {chosen_sku} not in catalog -> falling back to {fb}",
                flush=True,
            )
            chosen_sku = fb

        out = out.replace(src_sku, chosen_sku)
        total += count
        print(f"[g1-acq] Rewrote: {src_sku} -> {chosen_sku} (x{count} occurrences)", flush=True)

    if total > 0:
        flow.response.set_text(out)
        print(f"[g1-acq] Successfully rewrote {total} SKU occurrences!", flush=True)
    else:
        print("[g1-acq] No matching iOS target SKUs found in this response.", flush=True)
