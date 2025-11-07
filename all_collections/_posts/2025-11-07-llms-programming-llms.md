---
layout: post
title: LLMs are pretty good at programming LLMs
date: 2025-11-07
categories: ["AI", "LLM", "prompt engineering", "machine learning"]
description: Using Claude to improve the prompts that Claude uses for data labeling. How recursive prompt engineering achieved 90%+ accuracy.
---

I'm building a training data pipeline where an LLM labels samples for a DeBERTa-v3 model.

A little plot twist: I used Claude to improve the prompt that Claude uses to label the data.

## The Starting Point

My initial prompt was basic. I gave Claude a taxonomy and some text and asked how it would classify that text.

Results? Mediocre. Made-up categories. Inconsistent formatting. About 60% accuracy.

So I asked Claude: "How can I improve this prompt?"

## Claude's Suggestions

It suggested:
- Few-shot examples (show don't tell)
- Chain-of-thought reasoning (explain before answering)
- Structured XML delimiters (clear sections)
- Explicit JSON schemas (no ambiguity)

I implemented all of it. Accuracy jumped to 85%+.

I even had Claude optimize my few-shot examples for maximum impact.

Then I asked Claude to review the improved prompt. It found edge cases I missed. More improvements. Now pushing 90%+ accuracy.

## The Workflow

1. Write prompt → Test on samples
2. Ask Claude: "What's wrong with this prompt?"
3. Implement suggestions → Test again
4. Repeat until satisfied

Even as accuracy improved, there were rare occasions where Claude would invent categories that didn't exist in the taxonomy. You could usually figure out what it meant, but it needed fixing.

Again, I asked Claude to identify the root cause and suggest corrections.

It did—in minutes. Way faster than if I'd tested alternate prompt versions programmatically or by hand.

## The Meta Part

This all feels very meta: having an LLM assist in programming itself.

This isn't just about prompt engineering.

It's about using AI to understand AI's weaknesses—and fix them.

The best part? The improved prompts work better across different LLMs too. The clarity helps all models, not just Claude.

## Meta-lesson

Don't just use LLMs. Use LLMs to teach you how to use LLMs better.

Are you using AI to improve your AI workflows? What's worked for you?

#AI #PromptEngineering #MachineLearning #LLM
