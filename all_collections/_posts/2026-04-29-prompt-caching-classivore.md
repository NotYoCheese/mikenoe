---
categories:
- Machine Learning
- LLM
- Anthropic API
- Classivore
date: 2026-04-29
description: Anthropic's prompt cache silently ignores blocks below a per-model token
  threshold. Mine were too small. Here's how the trap works and how to detect it.
layout: post
mastodon_host: mastodon.social
mastodon_id: '116489262428285685'
mastodon_user: mikenoe
permalink: /posts/prompt-caching-classivore/
title: I Added Prompt Caching to My Labeling Pipeline. The Hit Rate Was Zero.
---
I'm building Classivore, a content classification API. The labeling pipeline that produces training data uses Anthropic's Batch API with Haiku 4.5 — two-stage classification, with the same large system prompt across thousands of pages per batch. On paper, it's a textbook prompt-caching use case.

I added caching. The cache hit rate stayed at 0%.

Here's what was actually happening, and why I left caching as a option which defaults to false.

## Why caching looked like an obvious win

Anthropic's prompt cache lets you mark a stable prefix of a prompt as cacheable. Subsequent requests within the TTL that share that prefix read from cache instead of re-tokenizing, at roughly 10x cheaper than input pricing. Two TTLs are available: 5-minute (default, cheap to write) and 1-hour (more expensive write, pays off across longer windows).

My labeling pipeline does two stages with Haiku 4.5:

- **Stage 1** — tier-1 triage. The system prompt contains the IAB 2.2 taxonomy outline (~700 categories with names and brief descriptions). Same prompt for every page in a batch.
- **Stage 2** — subtree drill-down. The system prompt contains only the subtree under the tier-1 hits. Different per page, but pages flagged into the same subtree share a prompt.

Stable system prompt + variable user message is exactly the shape Anthropic markets prompt caching for. I added `cache_control` blocks to both stages with a 1-hour TTL, extended my token-usage logging to capture `cache_creation_input_tokens` and `cache_read_input_tokens`, and ran a real corpus through it.

## What the numbers said

Cache hit rate: 0%. Across stages, across runs.

I expected at least *some* hits. Even if the economics didn't work out, the mechanism should have been writing a cache on the first request and reading it on the second. Zero meant the cache wasn't engaging at all.

## The silent threshold

Two compounding issues. The first one was the trap.

Each Anthropic model has a minimum cacheable token count. If the block you mark with `cache_control` is below that threshold, the API silently ignores it and bills you as if `cache_control` weren't there. No error, no warning, no telemetry. The request just doesn't cache.

The thresholds, per [Anthropic's prompt caching docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching):

| Model | Minimum cacheable tokens |
|---|---|
| Opus 4.7 / 4.6 / 4.5 | 4,096 |
| Opus 4.1 / 4 | 1,024 |
| Sonnet 4.6 | 2,048 |
| Sonnet 4.5 / 4 | 1,024 |
| Haiku 4.5 | 4,096 |

These values vary by model and have shifted upward across recent revisions. Re-verify against the current docs before relying on a number from any third-party post — including this one.

My stage-1 system prompt clocked in around 1,064 tokens. Under the bar for every current model, including Haiku 4.5's 4,096 minimum by close to three thousand tokens. Of the 29 distinct stage-2 subtrees, 20 were under 2,048 tokens; against the documented 4,096 bar, that count goes up further. Only the very largest subtrees (Sports, Entertainment) came close to qualifying, and those didn't get enough hits per batch to amortize the more-expensive cache-write rate.

I missed this in the first pass because I trusted the API. Caching looked enabled. Token counts looked fine in eyeball estimates. The response objects came back successful. The only signal that something was wrong was `cache_read_input_tokens` staying flat at zero in the usage payload.

## Even after the threshold, the math was tight

Haiku 4.5 batch pricing per million tokens: input $0.50, output $2.50, cache-write-1h $1.00, cache-read $0.05 ([API pricing](https://docs.anthropic.com/en/about-claude/pricing)). The 1-hour cache write costs 2x base input; cache reads cost 0.1x. Break-even on a 1-hour TTL cache works out to about 1.11 reads after the initial write. In practical terms, you need at least two cache hits within the TTL window for caching to be worth the elevated write rate.

Within a single batch run that's easy: one write, then N reads. But the 1-hour cache only pays off if it sticks across batches, and my batches were spaced unpredictably. Some days I'd run several in an hour. Some weeks I'd run one. Most cache writes were going to expire unread.

The dominant problem was the threshold (cache silently disabled), not the break-even ratio. But even if I'd fixed the threshold, the economics for *my* workload were borderline.

## Where the code stands now

Caching is opt-in, off by default. The runtime knobs are in place for a future operator to flip it on without re-engineering anything:

- Config flag: `labeling.prompt_cache` (default `false`)
- CLI override: `--prompt-cache` / `--no-prompt-cache` on the label command
- A `_cacheable_system()` helper that returns either a `cache_control`-marked block list (when enabled) or a plain string (when disabled)
- Token usage logging still records cache fields when present, so a future cache-on run produces useful telemetry from the first request

The CHANGELOG entry for v1.3.0 reads: "Add opt-in prompt caching for stage-1 and stage-2 system prompts via cache_control blocks with 1-hour TTL." That's intentionally factual. The feature exists; whether it pays off is the operator's call given their workload.

## When this changes

Don't dismiss prompt caching as broken. It just doesn't fit my current shape. Conditions that would change the calculus:

1. **A larger taxonomy.** [IPTC Media Topics](https://iptc.org/standards/media-topics/), used widely in news and contextual classification, has ~1,200 terms across five hierarchy levels. Rendered with names and short descriptions, that easily clears Haiku 4.5's 4,096 threshold and would cache cleanly. IAB 3.1 doesn't help (704 categories vs. 2.2's 698, similar token weight), but a switch to IPTC would.
2. **Switching to Opus 4.1 or Sonnet 4.5.** Both have a 1,024-token minimum that my 1,064-token prompt just clears — by 40 tokens, which is uncomfortably close to the noise floor of tokenization variation. Anthropic [deprecated](https://docs.anthropic.com/en/docs/about-claude/model-deprecations) the older 4-series Opus and Sonnet on April 14, 2026, retiring them on June 15, and the newer flagships (Sonnet 4.6 at 2,048, Opus 4.5+ at 4,096) raised the bar above where my prompt sits. Soon there won't be a current Anthropic model where this prompt caches without padding.
3. **Online endpoint instead of batch.** A live endpoint with hot prompts — the same system prompt being hit every few seconds — flips the math. The 5-minute TTL has a smaller write premium (1.25x vs. 2x for 1-hour) and a break-even of about 0.28 reads, so the first hit after the write already pays it off. Cache reads themselves refresh the TTL, meaning a steady traffic stream keeps the prefix cached well past the nominal 5 minutes. On a hot endpoint, caching is essentially free.
4. **Padding the prompt deliberately.** I could concatenate examples into the stage-1 prompt to push it above 4,096 tokens. But that's paying for tokens I don't need to enable a cache I'm not sure I'd hit.

## What I'd tell the next person enabling this

- Don't trust eyeball estimates of prompt size. Run `count_tokens` on the actual rendered prompt against the model-specific minimum. Crossing the threshold is binary, not gradual.
- The API returns success when `cache_control` is silently ignored. The only way to confirm caching is actually working is to inspect `cache_read_input_tokens` in the response usage object. If it stays at zero across requests that should hit, caching isn't engaging.
- Re-measure when you change the prompt or the taxonomy. Crossing the model-specific threshold in either direction silently flips behavior.
- Opt-in is the right default. Don't flip it on globally without telemetry showing the hit rate is real.

The feature is in the code. The flag is off. That's deliberate. The tooling tells me when caching will pay, and right now it won't.

---

**Have you hit the silent-threshold trap with prompt caching, or found a workload shape where it really pays off? I'd be curious to compare notes.**
