---
layout: post
title: Building an Agent to Solve My Training Data Problem
date: 2025-12-12
categories: ["Machine Learning", "AI", "Agents", "LangGraph", "Data Engineering"]
description: When no public dataset exists and manual labeling won't scale, I built a LangGraph agent that adaptively searches, scrapes, and labels training data. Here's how it filled 687 out of 698 categories in days.
mastodon_host: mastodon.social
mastodon_user: mikenoe
mastodon_id: 115708769710616523
---

I needed 25,000+ labeled samples across 698 categories. No public dataset came close. Manual labeling wouldn't scale. So I built an agent to do it.

## The Problem

I'm building a multi-label text classifier with 698 categories. The class distribution is brutal—"Technology" and "Sports" have abundant content everywhere, but try finding quality training samples for "Hobbies & Interests: Beekeeping" or "Music and Audio: Adult Album Alternative."

This is the long-tail problem. And it's a killer for multi-label classification.

I started with Common Crawl. Scraped a bunch of content, had an LLM label it. Results were predictable: excellent coverage for head categories, near-zero for the tail. Out of 698 categories, maybe 200 had decent representation.

## The Approaches That Didn't Work

**Manual web search + LLM labeling**: I'd search for "beekeeping articles," scrape them, run them through my labeling prompt. It worked, but it took forever. At this rate, filling 500+ categories would take months.

**Bulk LLM search queries**: I wrote a script that looped through weak categories and asked Claude to find relevant URLs. Better, but the searches weren't creative enough. For niche categories, the first page of search results is often irrelevant. I needed something that could adapt.

**More aggressive Common Crawl filtering**: Tried filtering CC data by keywords. The problem is that keyword matching and actual category relevance don't align well. An article mentioning "bees" once isn't necessarily about beekeeping.

## The Insight

What I needed wasn't a script—it was a system that could:
1. Identify which categories are weak
2. Generate smart search queries for those categories
3. Try different search strategies when one fails
4. Evaluate its own results and adjust

In other words: an agent.

## Building the Data Expansion Agent

I used LangGraph to build a stateful workflow. The core loop:

```
Analyze → Search → Scrape → Label → Evaluate → Repeat
```

Each node has a specific job:

**Analyze**: Load my labeled dataset, count samples per category, identify everything under 20 examples.

**Search**: For each weak category, generate a search query and hit the Brave Search API. But here's the key—the query generation is handled by Claude, not by string templates.

**Scrape**: Take the URLs, run them through my scraping pipeline.

**Label**: Run scraped content through my [LLM labeling prompt](/posts/llms-programming-llms/).

**Evaluate**: Check progress. Did we actually improve coverage? Which categories are still weak?

Then loop back to Analyze with updated state.

## The Agent Architecture

```
┌─────────────────┐
│ Analyze         │
│ Categories      │
└────────┬────────┘
         │
         ▼
    ┌────────┐     ┌──────────┐
    │ Enough │────►│   END    │
    │ Data?  │     └──────────┘
    └────┬───┘
         │ No
         ▼
┌─────────────────┐
│ Search for      │
│ Content         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Scrape          │
│ Content         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Label           │
│ Content         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Check           │
│ Progress        │
└────────┬────────┘
         │
         └─────► (Loop back to Analyze)
```

The state object tracks everything: which categories need data, how many times we've searched for each, what URLs we've already seen, total examples added.

## Adaptive Search Queries

This is where Claude earns its keep. Instead of template queries like `"{category}" articles`, I ask Claude to generate queries optimized for finding relevant content:

```python
prompt = f"""Generate a web search query to find content about: "{category}"

This is attempt #{attempt + 1} of 3. Vary your approach:
- Attempt 1: Authoritative content (news, expert blogs)
- Attempt 2: Educational content (guides, tutorials)  
- Attempt 3: Niche content (case studies, analysis, recent trends)

Return ONLY the search query."""
```

For "Hobbies & Interests: Beekeeping," attempt 1 might generate `beekeeping best practices expert guide`. If that doesn't yield good results, attempt 2 tries `beginner beekeeping tutorial how to start`. Attempt 3 might go for `urban beekeeping 2024 trends case study`.

The agent tracks which strategies have been tried and doesn't repeat failed approaches.

## Cost Efficiency

Running Claude + Brave Search + scraping at scale gets expensive fast. A few design choices kept costs reasonable:

**Batching**: Search for 3-5 categories per iteration, not one at a time. Scrape all URLs in one batch. Label in bulk.

**Smart stopping**: Each category gets max 3 search attempts. After that, it's marked as exhausted. No point throwing money at categories where content doesn't exist.

**Deduplication**: Track all URLs globally. Don't re-scrape or re-label content we've already seen.

**Early termination**: Stop when a category hits 20 examples. Don't over-collect.

## The Excluded Categories

Some categories are just impossible to find training data for. "Music and Audio: Soft AC Music" isn't a content category—it's a radio format. "Business and Finance: Large Business" is too vague to search for meaningfully.

I maintain an exclusion list:

```python
EXCLUDED_CATEGORIES = {
    "Music and Audio: Soft AC Music",
    "Music and Audio: Adult Album Alternative", 
    "Music and Audio: Urban AC Music",
    "Business and Finance: Large Business",
    # ...
}
```

The agent skips these entirely. No point wasting API calls on categories that can't be filled.

## Results

The agent ran for about a week, with me monitoring and occasionally adjusting the exclusion list.

**Before**: ~200 categories with 20+ examples
**After**: 687 out of 698 categories with 20+ examples

The remaining 11 categories are legitimately impossible to find quality English content for. They're in the exclusion list now.

Total labeled dataset: 26,754 samples.

## What I Learned

**Agents are for adaptive problems.** If I could have written a deterministic script, I would have. The value of the agent was in handling the long tail—categories where the first search strategy fails and you need to try something different.

**LLMs are good at generating search queries.** Better than I expected. Claude understood that "Adult Album Alternative" needed different search terms than "Beekeeping" and adjusted accordingly.

**The 80/20 rule applies to data collection too.** Getting from 200 to 600 categories was fast. Getting from 600 to 687 took longer. Those last 87 categories required the most creative search strategies.

**Some categories can't be filled.** And that's okay. Knowing which categories to exclude is as valuable as filling the ones you can.

## The Bigger Picture

This data collection was just one piece of the puzzle. The full journey:

1. **Failed baseline** (F1: 0.0015) — class imbalance so severe the model learned nothing
2. **Data quality fixes** (F1: 0.22) — filled obvious gaps in training data
3. **[Focal loss optimization](/posts/focal-loss-breakthrough/)** (F1: 0.51) — systematic grid search found α=0.75, γ=3.5
4. **Data expansion agent** (this post) — filled 687/698 categories
5. **Model architecture upgrade** (F1: 0.66) — DeBERTa-large over base gave +28.5%
6. **Per-category thresholds** (F1 macro: 0.69) — optimized thresholds independently per category

The agent solved the data bottleneck. But data alone didn't get me to production quality. It took the combination of good data, the right loss function, appropriate model capacity, and threshold optimization.

## Code

The agent code is part of a larger project, but the core pattern is reusable:

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)

workflow.add_node("analyze_categories", analyze_categories)
workflow.add_node("search_for_content", search_for_content)
workflow.add_node("scrape_content", scrape_content)
workflow.add_node("label_content", label_content)
workflow.add_node("check_progress", check_progress)

workflow.set_entry_point("analyze_categories")

workflow.add_conditional_edges(
    "analyze_categories",
    should_continue_searching,
    {"search": "search_for_content", "end": END}
)

workflow.add_edge("search_for_content", "scrape_content")
workflow.add_edge("scrape_content", "label_content")
workflow.add_edge("label_content", "check_progress")

workflow.add_conditional_edges(
    "check_progress",
    should_continue_iteration,
    {"continue": "analyze_categories", "end": END}
)

graph = workflow.compile()
```

The magic isn't in the graph structure—it's in the state management and the adaptive query generation. Track what you've tried, learn from what worked, adjust your approach.

## When to Build an Agent vs. a Script

Build a script when:
- The task is deterministic
- You can define success criteria upfront
- Failure modes are predictable

Build an agent when:
- You need adaptive behavior
- Different inputs require different strategies
- The system needs to evaluate its own progress

My data collection problem needed an agent because "search for beekeeping content" and "search for urban AC music content" require fundamentally different approaches. A script would have failed on the long tail.

---

**Have you built agents for data collection or other ML workflows? What patterns worked for you?**

