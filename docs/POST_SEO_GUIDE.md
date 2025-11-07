# Post SEO Guide

When creating new blog posts, add these optional fields to your frontmatter to improve search engine visibility and social media sharing:

## Recommended Frontmatter

```yaml
---
layout: post
title: Your Post Title
date: YYYY-MM-DD
categories: ["category1", "category2"]
description: A brief 150-160 character summary of your post. This appears in search results and social media.
image: /assets/images/post-cover-image.png
---
```

## Field Descriptions

### `description` (Recommended)
- **Purpose**: Used as the meta description in search results and social media previews
- **Length**: 150-160 characters (optimal for Google search results)
- **Example**: "How I used Claude to improve prompts that Claude uses to label training data, achieving 90%+ accuracy"
- **Impact**: Critical for CTR (click-through rate) from search results

### `image` (Recommended)
- **Purpose**: Used for social media preview images (Twitter, LinkedIn, Mastodon)
- **Path**: Relative to site root (e.g., `/assets/images/my-image.png`)
- **Size**: Ideally 1200x630px for optimal social sharing
- **Impact**: Better engagement on social platforms

## Current Posts Without Descriptions

To improve search visibility, consider adding descriptions to:
- `2025-10-31-llms-as-a-software-development-tool.md`
- `2025-11-07-llms-programming-llms.md`
- `2024-09-03-finally-made-site.md`
- `2021-11-04-jekyll-markdown.md`

## SEO Setup Summary

✅ **Already configured:**
- jekyll-seo-tag plugin (auto-generates schema markup)
- Sitemap generation (sitemap.xml)
- RSS feed (feed.xml)
- robots.txt (search engine crawler permissions)

📝 **Next steps:**
- Add descriptions to existing posts
- Create/add cover images for key posts
- Monitor search performance in Google Search Console
