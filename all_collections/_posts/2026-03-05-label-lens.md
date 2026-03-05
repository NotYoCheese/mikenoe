---
layout: post
title: "I Built a Tool to Find the Problems in My Training Data"
date: 2026-03-05
categories: ["Machine Learning", "Data Quality", "Side Project"]
description: "LabelLens analyzes labeled text classification datasets for duplicates, mislabels, and class imbalance — and it already found real issues in my own data."
---

I've been working on a text classification pipeline for IAB content categorization. Tens of thousands of labeled web pages, hundreds of categories. The kind of dataset where problems hide in plain sight.

So I built a tool to find them.

## LabelLens

[LabelLens](https://huggingface.co/spaces/mikenoe/label-lens) is a Streamlit app that takes a CSV with text and label columns and runs a battery of quality checks:

**Class distribution analysis.** Imbalance ratios, effective number of classes, long-tail detection. If two of your classes have less than 1% of the data, you probably want to know that before training.

**Duplicate detection.** Exact duplicates and near-duplicates via TF-IDF cosine similarity. The critical finding here is cross-class duplicates — the same text appearing with different labels. That's a labeling error, full stop.

**Label noise scoring.** A logistic regression trained with stratified k-fold cross-validation scores every sample's confidence. The ones where the model is least confident about the given label are your mislabel candidates. It's not proof, but it's a strong signal for where to focus manual review.

**Actionable report.** Everything rolls up into severity ratings (Critical, Warning, Info) with specific recommendations.

## What It Found in My Data

The first real dataset I ran through LabelLens was 26,754 labeled web pages from my IAB classification project. I expected it to be clean — I had deduplication in my collection pipeline.

It found 5,664 exact duplicates.

When I dug into what those duplicates actually were, the pattern was clear. My scraper was deduplicating by URL, not by content. So different URLs on the same site that served identical text — cookie consent banners, privacy policy boilerplate, site registration prompts — all slipped through as "unique" pages.

The worst offender was a cookie notice that appeared 65 times across different pages, each labeled with a different content category. Same text, different labels. That's exactly the kind of noise that degrades a classifier.

I wouldn't have caught this by looking at accuracy metrics. The model would have memorized the boilerplate and predicted whatever label appeared most often for it. LabelLens surfaced it in seconds.

## How It Works

The architecture is intentionally simple. Each analysis module is stateless — it takes a DataFrame and returns a dict. No classes, no framework, no orchestration layer. Just functions.

- **ingest.py** — Auto-detects text and label columns, validates the dataset
- **distribution.py** — Class counts, imbalance ratio, entropy-based effective class count
- **duplicates.py** — Exact match plus TF-IDF cosine similarity for near-dupes
- **noise.py** — Cross-validated logistic regression confidence scoring
- **report.py** — Aggregates findings into severity-rated recommendations

For large datasets, the expensive analyses (near-duplicates and noise scoring) run on a configurable sample. Distribution and exact duplicates always use the full dataset.

## Try It

You can use it right now — upload any CSV with text and label columns:

- **Live app:** [huggingface.co/spaces/mikenoe/label-lens](https://huggingface.co/spaces/mikenoe/label-lens)
- **Source:** [github.com/NotYoCheese/label-lens](https://github.com/NotYoCheese/label-lens)

A sample dataset is included if you just want to poke around.

If you're training text classifiers on real-world data, you almost certainly have quality issues you haven't found yet. The question is whether you find them before or after they show up in your model's predictions.

---

**What does your training data quality workflow look like? I'd be curious to hear what tools or processes others are using.**
