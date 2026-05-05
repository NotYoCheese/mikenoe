---
categories:
- AI
- Web Scraping
- Infrastructure
- ML Engineering
date: 2026-05-05
description: A real-world benchmark of curl_cffi against a 252-URL fixture set. Success
  rate went from 37% to 78% with a one-library swap and a 22-line deletion. Why TLS
  fingerprinting is the dominant signal modern WAFs use, and what AI engineers building
  data pipelines need to know.
layout: post
mastodon_host: mastodon.social
mastodon_id: '116523552508974611'
mastodon_user: mikenoe
title: Doubling Scraper Success Rate by Mimicking Chrome's TLS Handshake
---
Most Python code that fetches web pages gets blocked by half the internet, and the standard advice (rotate User-Agents, add proxies) makes it worse, not better.

I just measured the alternative on a 252-URL fixture set representative of what Classivore (my classification API) needs to fetch:

- Baseline (`requests` + UA rotation + manual browser headers): **37.3% success**
- `curl_cffi` impersonating Chrome 131, with my old defensive headers stripped: **78.2% success**
- Median latency cost: ~500ms
- Paid fallback API usage: down 64%

This post is what I learned getting there. The headline is the result. The interesting parts are the mental model for why TLS fingerprinting works the way it does, the 2×2 experiment that separated fingerprint effects from IP-reputation effects, and the counterintuitive finding that deleting 22 lines of "defensive" header code added another two percentage points.

## The problem

Classivore is a multi-label text classifier serving an API. One endpoint takes a URL and returns IAB taxonomy categories. That endpoint needs to fetch the URL, extract its main text content, and run inference. Reliability of the fetch step is a hard constraint: every failed fetch either degrades the user's result or forces a fallback to a paid third-party search API.

When I started measuring, the fetch layer was failing 60%+ of the time on a representative URL set. Classic Python stack: `requests`, a rotating `User-Agent` pool, a hand-curated `BROWSER_HEADERS` dict copied from Chrome's DevTools.

The internet's standard advice for this problem is wrong. "Rotate User-Agents" doesn't work. "Add proxies" doesn't work alone. Both can make detection worse. To understand why, you have to understand what modern Web Application Firewalls actually fingerprint.

## What WAFs actually fingerprint

The User-Agent header is a freeform string the client claims about itself. It is trivially spoofable, and modern bot-detection systems treat it as approximately worthless. They look at signals that are hard to fake from a generic Python stack.

### JA3 and JA4: TLS ClientHello fingerprints

When your TLS client opens a connection, the very first message it sends is the ClientHello. This message contains a list of TLS versions, cipher suites, extensions, supported elliptic curves, signature algorithms, and so on. Different TLS implementations produce different ClientHellos: not because the spec requires them to, but because each implementation made different choices about ordering, defaults, and which optional extensions to send.

JA3 (from Salesforce, 2017) hashes a subset of these fields into a single MD5 string. JA4 (from FoxIO, 2023) is the modern successor: it sorts the fields before hashing (defeating GREASE-based randomization that broke JA3) and produces a human-readable fingerprint like `t13d1516h2_8daaf6152771_e5627efa2ab1` (a real Chrome JA4). The first segment is human-readable: `t` for TCP, `13` for TLS 1.3, `d` for domain SNI, `15` cipher suites, `16` extensions, `h2` ALPN. The second segment is a truncated SHA256 over the sorted cipher list. The third is a truncated SHA256 over sorted extensions plus signature algorithms.

<figure>
  <img src="/assets/images/ja4-anatomy.svg" alt="Anatomy of a JA4 fingerprint, decomposing t13d1516h2_8daaf6152771_e5627efa2ab1 into its three sections and showing how the first section breaks into protocol, TLS version, SNI presence, cipher count, extension count, and ALPN."/>
  <figcaption>The anatomy of a Chrome JA4 fingerprint.</figcaption>
</figure>

Concrete example: Chrome on macOS produces a ClientHello with a specific cipher order, GREASE values inserted at known slots, and a specific extension list including `application_settings` (ALPS). Python's `requests` library uses urllib3, which uses OpenSSL or Python's built-in `ssl` module. OpenSSL by itself cannot produce Chrome's exact ClientHello: wrong cipher order, no GREASE in the right places, missing extensions, different signature algorithm preferences. Your TLS handshake is a fingerprint of your stack, and it leaks the stack identity before any HTTP byte is sent.

### HTTP/2 SETTINGS frames and pseudo-header order

HTTP/2 is a binary protocol with multiplexed streams. When a client opens an HTTP/2 connection, it sends a `SETTINGS` frame with values for things like `HEADER_TABLE_SIZE`, `INITIAL_WINDOW_SIZE`, and `MAX_HEADER_LIST_SIZE`. Different stacks send different defaults. Chrome 131 sends one set of values; Go's `net/http` sends another; Python's `httpx` sends a third.

There is also pseudo-header order. The HTTP/2 spec requires four pseudo-headers (`:method`, `:authority`, `:scheme`, `:path`) but does not mandate their order. Chrome sends them in one order; Go sends them in a different order; Python stacks have their own order. This alone is enough to identify the implementation.

Akamai's Elad Shuster published a paper at Black Hat Europe 2017, ["Passive Fingerprinting of HTTP/2 Clients"](https://blackhat.com/docs/eu-17/materials/eu-17-Shuster-Passive-Fingerprinting-Of-HTTP2-Clients-wp.pdf), describing this fingerprinting technique and the format `S[settings]|WU[window_update]|P[priorities]|HEADERS[order]`. Modern WAFs use it. Combined with JA4, this is enough to identify almost any non-browser client with high confidence, regardless of what User-Agent it claims.

### Why UA rotation is worse than nothing

Here is the trap. If you send Chrome's User-Agent header from a Python `requests` connection, you have made the bot signal *stronger*, not weaker. The WAF now sees:

- Claimed identity: Chrome 131 on Windows
- TLS handshake fingerprint: Python `requests` (or `httpx`)
- HTTP/2 settings: Python defaults

This mismatch is itself a high-confidence bot signal. WAFs cross-check the OS claim in the User-Agent against the OS implied by the TLS fingerprint, and against the HTTP/2 SETTINGS values. A consistent set of mismatches across these signals is more identifying than any single one.

The implication: with a generic Python TLS stack, you are better off sending Python's actual User-Agent than Chrome's. The WAF was going to fingerprint you regardless, and at least the consistent identity does not raise the "actively trying to deceive" flag.

## What curl_cffi actually does

The fix is not to spoof the User-Agent. The fix is to produce a TLS handshake and HTTP/2 framing that look like Chrome on the wire.

`curl_cffi` is a Python CFFI binding around `curl-impersonate`, a project by lwthiker that maintains patches against BoringSSL (Chrome's TLS library) and NSS (Firefox's TLS library). The patches force exact cipher and extension ordering per browser version, inject GREASE values at the right slots, add browser-specific TLS extensions like ALPS, configure HTTP/2 SETTINGS to match real browser defaults, and reorder HTTP/2 pseudo-headers correctly.

The API mirrors `requests`:

```python
from curl_cffi import requests

resp = requests.get("https://example.com", impersonate="chrome131")
```

Under the hood, that call goes through patched libcurl, which uses patched BoringSSL, which produces a wire-level handshake that matches a real Chrome 131 connection. Not approximately. Byte-for-byte. The libraries producing the traffic are real browser libraries with the right patches applied.

## The experiment

I wanted clean data, not anecdotes. The benchmark uses a 252-URL fixture set covering news, e-commerce, sports, social, lifestyle, technology, and reference sites. The URLs follow a Zipfian frequency distribution that mirrors what an ad tech contextual classifier sees in a prebid bidstream: a few high-volume publisher domains dominate, with a long tail of smaller sites. Each run records HTTP status, byte count, extracted character count, fetch latency, extract latency, block markers detected, and outcome classification (`ok`, `empty_extraction`, `http_error`, `blocked`, `timeout`).

To separate TLS fingerprint effects from IP reputation effects, I ran a 2×2:

<figure>
  <img src="/assets/images/fingerprint-ip-2x2.svg" alt="A 2x2 matrix showing success rate by TLS fingerprint and egress IP. Baseline requests on local M1 scored 37.3 percent, baseline on Hetzner 39.3 percent, curl_cffi on local M1 76.6 percent, and curl_cffi on Hetzner 68.3 percent. Fingerprint mimicry adds 29 to 39 percentage points; IP type contributes only 2 to 8 points depending on whether fingerprint is clean."/>
  <figcaption>The 2×2 separates fingerprint effects from IP reputation effects. Fingerprint dominates; IP is second-order.</figcaption>
</figure>

Then a follow-up experiment removed the lingering manual `BROWSER_HEADERS` and `USER_AGENTS` rotation that had been sitting on top of `curl_cffi`, letting the Chrome 131 impersonation profile own the entire header set.

| | with manual headers | clean headers |
|---|---|---|
| **local M1 Max** | 76.6% | 78.2% |
| **Hetzner** | 68.3% | 70.6% |

## What the data says

**Fingerprint is the dominant lever.** TLS impersonation is worth +29 to +39 percentage points regardless of egress IP. This is not subtle. It is by far the largest single intervention available for fetch reliability.

**IP reputation is real but second-order.** Datacenter vs residential IP is worth ~8 pp on top of fingerprint, ~2 pp without it. The two effects interact: IP gating only becomes visible after fingerprint gating clears. If your scraper is failing on TLS fingerprint, you cannot tell whether your IP is being penalized; the WAF stops you before that signal applies.

**Some hosts gate on both axes.** A 24-URL set works on local-curl_cffi but fails on Hetzner-curl_cffi. These hosts (Bloomberg, Politico, Etsy, Stack Overflow, Reddit, Old Navy, others) gate on (clean fingerprint AND non-datacenter IP). If you need them, residential proxy egress for that subset is the right intervention. Most production scrapers do not need them, and routing only the hosts that require it through a paid proxy is more cost-effective than routing everything.

**There is no IP-reputation winner without fingerprint.** Under bare `requests`, the local-vs-Hetzner success rate delta is +2 pp, basically noise. Different services run different rules; some prefer datacenter ranges (better for predictability), some prefer residential (better for "real user" signals). Without fingerprint mimicry, IP choice is a coin flip.

## The hidden category

The most surprising finding came from inspecting failures.

Out of the 99 newly-OK URLs after the curl_cffi swap on local, 69 were not previously failing as `http_error`. They were failing as `empty_extraction`: HTTP 200 returned, large body, but no extractable article text after running it through trafilatura.

Those bodies were Cloudflare interstitials. The "Just a moment..." challenge page. Substantial HTML that contains JavaScript challenges and no actual article content. My extractor was correctly producing zero characters; the failure was upstream.

I had been considering a third extractor fallback to address the empty-extraction tail. The tail was not an extraction problem. It was a TLS fingerprint problem disguised as an extraction problem. After curl_cffi, the empty-extraction count dropped from 105 to 42 because Cloudflare started serving the actual article HTML instead of the challenge page.

Lesson: when a failure mode looks like a content-processing problem, check whether the content was the real content. WAF interstitials returning HTTP 200 with substantial bodies are easy to mis-attribute.

## Deleting 22 lines that were hurting

After the curl_cffi swap, my scraper still had its old `BROWSER_HEADERS` dict and `USER_AGENTS` rotation list intact, applied as `headers=` and `User-Agent` overrides on every `curl_cffi` request. Belt-and-suspenders, I told myself.

A pre-experiment header dump revealed what was actually happening. `curl_cffi` with `impersonate="chrome131"` automatically sets a coordinated bundle: `Accept`, `Accept-Encoding`, `Accept-Language`, `Priority` (the HTTP/2 priority frame), `Sec-Ch-Ua`, `Sec-Ch-Ua-Mobile`, `Sec-Ch-Ua-Platform`, `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, `Sec-Fetch-Site`, `Sec-Fetch-User`, `Upgrade-Insecure-Requests`, and `User-Agent`. Internally consistent: the `Sec-Ch-Ua` brand list matches the major version in the `User-Agent` matches the platform claim in `Sec-Ch-Ua-Platform`.

My defensive code was overriding this. Three specific harms:

1. **UA/TLS-OS mismatch on two-thirds of requests.** `curl_cffi`'s TLS handshake fingerprints as Chrome 131 on macOS. My UA rotation replaced the matching User-Agent with Windows or Linux strings two times out of three. WAFs cross-check TLS-OS against UA-OS; the mismatch was a tell.
2. **Weaker `Accept` and `Accept-Encoding` values.** My hardcoded values missed `image/apng`, `application/signed-exchange;v=b3;q=0.7`, and `zstd`, all things real Chrome sends.
3. **Adding `DNT: 1`.** Chrome does not send DNT by default. Only the small subset of users who toggled "Do Not Track" do. Sending it is itself a fingerprint.

I deleted 22 lines of header-management code. Success rate went up 1.6 pp on local, 2.3 pp on Hetzner. Three hosts on the original "still failing under curl_cffi" residue list (Etsy, Inc.com, TheKitchn) recovered, validating that the residual was UA/TLS mismatch rather than something requiring a headless browser.

The principle: do not second-guess a tool that is doing one thing well. `curl_cffi` ships with a Chrome 131 profile that is internally consistent by construction and gets re-scraped from real Chrome periodically. A hardcoded dict in `headers.py` cannot stay in sync. Defense in depth on top of a precise tool is offense against yourself.

## What still does not work

The 22% still-failing breaks into three clean categories that validate a tiered fetching architecture.

**JS-rendered SPAs (~15 sites).** YouTube, TikTok, Reddit, Instagram, Facebook, Threads, Pinterest, Snapchat, Twitch, Tumblr, Quora, Substack, Hacker News, Imgur. These return HTTP 200 but the content needs JavaScript execution to render. No amount of TLS impersonation fixes this. Headless browser (Playwright) is the right escalation.

**Hard paywalls (~3 sites).** WSJ, Reuters, Barron's. Auth wall. Different problem entirely. Either you have credentials, you have a partnership, or you accept the gap and route to a different data source.

**Sophisticated behavioral and canvas detection (~10 sites).** Amazon, Costco, Wayfair, Etsy, Tripadvisor, H&M, Petco, Chewy, Inc, Surfer. These run JavaScript challenges, behavioral analysis, or canvas/WebGL fingerprinting. They need residential proxy plus headless browser. Expensive. Worth it only when the host is high-priority.

The right architecture is tiered:

<figure>
  <img src="/assets/images/tiered-fetching.svg" alt="Tiered fetching architecture showing three escalating tiers: Tier 1 curl_cffi handles fingerprint gating and 78 percent of fetches, Tier 2 Playwright handles JS-rendered SPAs and adds 6 percent, Tier 3 residential proxy with Playwright handles sophisticated bot detection and adds 4 percent. Hard paywalls are out of scope."/>
  <figcaption>The tiered fetching architecture. Each tier solves a specific failure mode; cost and complexity escalate together.</figcaption>
</figure>

Most production fetchers should be Tier 1 by default with Tier 2 escalation triggered on specific failure patterns. Tier 3 is host-specific and budget-bounded. Hard paywalls are a different problem entirely and should route to a different data acquisition strategy: partnerships, licensed feeds, paid search APIs, or accepting the gap.

## A note on cross-domain pattern recognition

I recognized the failure pattern fast because I spent 14 years in ad tech. Programmatic supply chains have been adversarial-engineering against TLS fingerprinting since 2017. Every DSP and SSP runs detection that uses these same signals to filter invalid traffic, identify fraud, and validate inventory. The WAFs serving Cloudflare and Akamai are the same kind of system, just facing the user instead of the buyer.

AI engineers building RAG pipelines, classification systems, and agentic data ingestion are walking into a problem space that ad tech walked into a decade ago. The defenses are mature; the offensive techniques are well-known among the people who fight this professionally. If you are building AI infrastructure that ingests web content at scale, the engineers who have worked the other side of this fight have asymmetric value right now. The patterns transfer.

## Reproducibility

The methodology is straightforward to reproduce. The 252-URL fixture covers a representative spread of news, e-commerce, social, sports, lifestyle, and reference sites. The bench tool records JSONL output per URL with HTTP status, latency, content size, extracted text length, and outcome classification. The same fixture was used across all four runs (baseline local, baseline Hetzner, curl_cffi local, curl_cffi Hetzner) plus the two clean-headers follow-up runs.

If you are running into similar reliability problems on a content fetcher, the order of intervention I would suggest, ranked by lift per hour of effort:

1. Swap to `curl_cffi` with a current Chrome impersonation profile.
2. Strip any manual `User-Agent` rotation and `BROWSER_HEADERS` overrides. Let the impersonation profile own the header set.
3. Reclassify your `empty_extraction` failures: a meaningful fraction may be WAF interstitials, not extractor problems.
4. Measure egress IP effect with a 2×2 before paying for residential proxies. Most of the win is fingerprint.
5. Build the tiered fallback architecture last. Most fetches should never need it.

The biggest mistake I made was treating the fetch problem as solved-enough to defer in favor of architectural work on the extractor. The fetch layer was the dominant constraint, and the lift was much larger than I had estimated. Measure first.

---

*Classivore is at [classivore.com](https://classivore.com).*

*Further reading:*

- *[FoxIO JA4+ specification](https://github.com/FoxIO-LLC/ja4)*
- *[Shuster, "Passive Fingerprinting of HTTP/2 Clients" (Black Hat EU 2017)](https://blackhat.com/docs/eu-17/materials/eu-17-Shuster-Passive-Fingerprinting-Of-HTTP2-Clients-wp.pdf)*
- *[curl-impersonate by lwthiker](https://github.com/lwthiker/curl-impersonate)*
- *[curl_cffi Python bindings](https://github.com/lexiforest/curl_cffi)*
