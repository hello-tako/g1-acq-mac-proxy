#!/usr/bin/env bash
set -euo pipefail

# start-proxy.sh — Zero-config launcher for the Google One (iOS) Promo SKU MITM Proxy.
# Automatically detects the host LAN IP, sets up a local Python virtualenv with mitmproxy,
# restricts TLS interception strictly to `one.google.com` (so Apple App Store / iCloud
# certificate pinning is never disrupted), and starts listening on port 8888.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
PORT="${G1_PROXY_PORT:-8888}"

detect_lan_ip() {
  local ip=""
  if command -v ipconfig >/dev/null 2>&1; then
    ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
  fi
  if [[ -z "${ip}" ]] && command -v hostname >/dev/null 2>&1; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  fi
  if [[ -z "${ip}" ]] && command -v ifconfig >/dev/null 2>&1; then
    ip="$(ifconfig | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}' || true)"
  fi
  echo "${ip:-127.0.0.1}"
}

LAN_IP="${G1_HOST_IP:-$(detect_lan_ip)}"
export G1_HOST_IP="${LAN_IP}"

echo "======================================================================"
echo "  g1-acq-mac-proxy — Free iOS Google AI Ultra Promo MITM Proxy"
echo "======================================================================"

if [[ ! -x "${VENV_DIR}/bin/mitmdump" ]]; then
  echo "[1/2] Creating Python virtual environment and installing mitmproxy..."
  PYTHON_BIN="$(command -v python3.11 || command -v python3.12 || command -v python3 || true)"
  if [[ -z "${PYTHON_BIN}" ]]; then
    echo "ERROR: python3 (3.10+) is required but was not found in PATH." >&2
    exit 1
  fi
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install --upgrade pip >/dev/null
  "${VENV_DIR}/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt"
fi

ESCAPED_IP="${LAN_IP//./\\.}"
ALLOW_REGEX="^(one\\.google\\.com|mitm\\.it|cert\\.local|${ESCAPED_IP})(:443|:${PORT})?$"

cat <<EOF

[2/2] Proxy is ready! Configure your iPhone / iPad on the same Wi-Fi:

  1. iOS Wi-Fi Proxy Settings:
     Settings -> Wi-Fi -> tap (i) next to your Wi-Fi -> scroll to bottom ->
     Configure Proxy -> Manual:
       Server: ${LAN_IP}
       Port:   ${PORT}
     Tap Save.

  2. Install & Trust the CA Certificate (One-Time Setup):
     a) Open Safari on iPhone and go to:
        http://${LAN_IP}:${PORT}
        Tap "Allow" to download the configuration profile.
     b) Open iOS Settings -> "Profile Downloaded" (or General -> VPN & Device Management)
        -> tap "mitmproxy" -> tap Install.
     c) CRITICAL STEP: Go to iOS Settings -> General -> About -> scroll to bottom ->
        "Certificate Trust Settings" -> toggle ON full trust for "mitmproxy".

  3. Trigger the Google AI Ultra 20TB / 30TB Discount in App Store:
     Open the Google App (colored G icon, NOT the standalone Google One app) ->
     tap your Profile Avatar (top-right) -> "Manage Google One" ->
     select the Ultra 20TB or 30TB plan and tap Subscribe.

  (When finished, set iOS Wi-Fi -> Configure Proxy back to Off.)
======================================================================
EOF

exec "${VENV_DIR}/bin/mitmdump" \
  --listen-host 0.0.0.0 \
  --listen-port "${PORT}" \
  --allow-hosts "${ALLOW_REGEX}" \
  -s "${SCRIPT_DIR}/g1_acq_mitm.py"
