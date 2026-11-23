# AI Agent Playbook (`AGENTS.md`)

This file provides a deterministic, step-by-step execution playbook for AI coding agents (Claude Code, Cursor, Antigravity, Windsurf, OpenAI Codex, etc.). When a user gives you this repository and asks you to set up the **free macOS / Linux MITM proxy for Google AI Ultra (iOS)**, follow these steps exactly.

---

## 1. Objective & Architecture

This tool replaces the paid iOS **Shadowrocket** app (\$2.99) with a **100% free local `mitmproxy` server** running on the user's Mac or Linux machine over the same Wi-Fi LAN as their iPhone or iPad.

- **Target URL**: `https://one.google.com/ai?...` (loaded inside the **Google App** on iOS via **Profile Avatar → Manage Google One**).
- **Rewrite Mechanism**:
  - `g1.ios.20tb.m.v2` → `g1.20tb.3months_ip_90p.acq` (fallback: `g1.20tb.3months_ip_75p.acq`)
  - `g1.ios.30tb.ai.pro.m` → `g1.ai.ultra.3months_ip_90p.acq` (fallback: `g1.ai.ultra.3months_ip_75p.acq`)
- **Strict TLS Allowlist**: Only `one.google.com` and the onboarding endpoints (`mitm.it`, `cert.local`, `<HOST_LAN_IP>`) are intercepted. All other domains (`*.apple.com`, `itunes.apple.com`, `accounts.google.com`, banking apps) bypass TLS MITM so Apple StoreKit and SSL certificate pinning never fail.
- **QUIC Downgrade**: Strips `Alt-Svc` response headers from `one.google.com` so the iOS Google App cannot switch to UDP 443 (HTTP/3 QUIC) and bypass the HTTP proxy.
- **1-Click Certificate Onboarding**: Directly serves `~/.mitmproxy/mitmproxy-ca-cert.pem` (`application/x-x509-ca-cert`) when the iOS device visits `http://<HOST_LAN_IP>:8888`, avoiding iOS Safari's automatic HTTPS upgrade on `mitm.it`.

---

## 2. Automated Agent Execution Steps

### Step 1: Detect Host LAN IP & Verify Python 3.10+
Run:
```bash
chmod +x ./start-proxy.sh
```
Detect the host's Wi-Fi LAN IP address:
- **macOS**: `ipconfig getifaddr en0 || ipconfig getifaddr en1`
- **Linux**: `hostname -I | awk '{print $1}'`

### Step 2: Start the MITM Proxy as a Background Daemon
Launch `./start-proxy.sh` in background/daemon mode so it stays alive while the user interacts with their iPhone:
```bash
./start-proxy.sh
```
*(Wait until you see `HTTP(S) proxy listening at *:8888` in the output).*

### Step 3: Instruct the User on iPhone / iPad
Present the detected `<HOST_LAN_IP>` and port `8888` to the user with these exact 4 steps:

1. **Configure iOS Wi-Fi HTTP Proxy**:
   - Open iOS **Settings → Wi-Fi** → tap the **`(i)`** icon next to the connected Wi-Fi network.
   - Scroll all the way to the **very bottom** of the page (under the *HTTP PROXY* section; do **not** touch *Configure IP* in the middle of the page, leave *Configure IP* on *Automatic*).
   - Tap **Configure Proxy → Manual**:
     - **Server**: `<HOST_LAN_IP>`
     - **Port**: `8888`
     - Tap **Save**.
2. **Download the CA Profile (1-Click Plain HTTP)**:
   - Open **Safari** on the iPhone and navigate to:
     `http://<HOST_LAN_IP>:8888`
   - Tap **Allow** when iOS prompts: *"This website is trying to download a configuration profile."*
3. **Install & Enable Full Root Certificate Trust (Both Switches Required)**:
   - Go to iOS **Settings → Profile Downloaded** (or **Settings → General → VPN & Device Management**) → tap **mitmproxy** → tap **Install**.
   - **CRITICAL**: Go to iOS **Settings → General → About** → scroll to the very bottom → tap **Certificate Trust Settings** → toggle **ON (Green)** the switch next to **mitmproxy** under *"Enable full trust for root certificates"*.
4. **Open Google App on iOS**:
   - Force-close and reopen the **Google App** (the multi-colored **G** icon from the App Store, **not** the standalone Google One app).
   - Tap the **Profile Avatar (top-right) → Manage Google One**.
   - Select the **Ultra** tab / modal and tap **Subscribe** on the **20 TB** or **30 TB** plan to launch the Apple App Store payment sheet with the 90%-off (or 75%-off) promotional SKU.

---

## 3. Log Monitoring & Diagnostic Verification for Agents

Monitor the `mitmdump` stdout log while the user performs the steps on their iPhone:

| Log Message | Diagnosis & Next Action |
| :--- | :--- |
| `[g1-acq] Served mitmproxy CA certificate profile directly to iOS client` | The iPhone successfully connected to the proxy and downloaded the `.pem` profile. Remind the user to install it and enable **Certificate Trust Settings**. |
| `Client TLS handshake failed. The client disconnected during the handshake... one.google.com` | The user installed the profile in *VPN & Device Management* but **forgot to toggle ON full trust** in **Settings → General → About → Certificate Trust Settings**. Guide them to toggle it ON. |
| `[g1-acq] Promotional (.acq) SKUs in account catalog: g1.20tb.3months_ip_90p.acq, ...` | The Google account is eligible for the `.acq` promo and the SKU replacement succeeded. The user can now tap **Subscribe** in the Google App to open the App Store sheet. |
| `[g1-acq] Promotional (.acq) SKUs in account catalog: NONE` | This specific Google account does not have `.acq` promotional SKUs in its server-side catalog. Note: If `NONE` is returned and the rewrite still executes, the iOS UI may hide the Ultra card because the `.acq` SKU is missing from the account's price dictionary. Switch to an eligible Google account (no active Google One subscription) or run with `G1_STRICT_CATALOG=1 ./start-proxy.sh` to skip rewriting on ineligible accounts. |
| iPhone has no internet connectivity at all | Check if the background `mitmdump` process stopped or if the host's LAN IP changed. Restart `./start-proxy.sh` or tell the user to set **Wi-Fi → Configure Proxy → Off** when finished. |
