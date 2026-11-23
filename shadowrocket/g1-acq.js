/**
 * g1-acq.js — Google One (iOS) Subscription SKU Mapper (Shadowrocket http-response script)
 *
 * Design Principles:
 *   1. Single Responsibility: Performs pure string replacement from standard iOS monthly
 *      product IDs to promotional introductory `.acq` product IDs. No telemetry or external network calls.
 *   2. Catalog-Aware Fallback: Scans the raw response body for available `.acq` SKUs first.
 *      If the primary 90%-off SKU (`90p.acq`) is absent from the catalog while the 75%-off
 *      fallback SKU (`75p.acq`) is present, automatically falls back to `75p.acq`.
 *   3. Data-Driven Configuration: All SKU mappings live in `SKU_MAP` and `FALLBACK`.
 *
 * Version: v6
 */
"use strict";

console.log("[g1-acq] v6 loaded");

/* Standard iOS monthly In-App Purchase ID -> Target 90%-off promotional ID */
var SKU_MAP = {
  "g1.ios.20tb.m.v2":     "g1.20tb.3months_ip_90p.acq",
  "g1.ios.30tb.ai.pro.m": "g1.ai.ultra.3months_ip_90p.acq"
};

/* Fallback 75%-off promotional ID if the 90%-off SKU is absent from the catalog */
var FALLBACK = {
  "g1.20tb.3months_ip_90p.acq":     "g1.20tb.3months_ip_75p.acq",
  "g1.ai.ultra.3months_ip_90p.acq": "g1.ai.ultra.3months_ip_75p.acq"
};

function occurrences(s, needle) {
  return needle ? s.split(needle).length - 1 : 0;
}

function run() {
  var body = $response && $response.body;
  if (typeof body !== "string" || body === "") {
    $done({});
    return;
  }

  /* Discover promotional .acq SKUs actually present in the response catalog */
  var raw = body.match(/g1\.[a-z0-9._]{2,60}acq/g) || [];
  var seen = {};
  var catalog = [];
  for (var r = 0; r < raw.length; r++) {
    if (!seen[raw[r]]) { seen[raw[r]] = 1; catalog.push(raw[r]); }
  }
  console.log("[g1-acq] Catalog .acq SKUs: " + (catalog.join(", ") || "NONE"));

  var out = body, total = 0;
  var froms = Object.keys(SKU_MAP);
  for (var k = 0; k < froms.length; k++) {
    var from = froms[k];
    var n = occurrences(out, from);
    if (n === 0) continue;

    var to = SKU_MAP[from];
    if (catalog.indexOf(to) === -1 && FALLBACK[to] && catalog.indexOf(FALLBACK[to]) !== -1) {
      console.log("[g1-acq] Primary SKU not in catalog, falling back: " + to + " -> " + FALLBACK[to]);
      to = FALLBACK[to];
    }

    out = out.split(from).join(to);
    total += n;
    console.log("[g1-acq] " + from + " -> " + to + " x" + n);
  }

  console.log(total ? "[g1-acq] Rewrote " + total + " occurrences" : "[g1-acq] No matches");
  $done(total ? { body: out } : {});
}

run();
