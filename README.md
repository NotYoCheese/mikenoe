# Mike Noe's Website

A Jekyll-based personal website hosted on GitHub Pages at [mikenoe.com](https://mikenoe.com).

## Setup

### Prerequisites
- Ruby 2.7 or higher
- Bundler

### Install Dependencies
```bash
bundle install
```

## Development

### Build the Site
```bash
bundle exec jekyll build
```

### Preview Locally
```bash
bundle exec jekyll serve
```

The site will be available at `http://localhost:4000`

### Incremental Builds (Faster)
```bash
bundle exec jekyll serve --incremental
```

## Creating Posts

1. Create a new file in `all_collections/_posts/` with the format: `YYYY-MM-DD-title.md`
2. Add frontmatter with required metadata:
```yaml
---
layout: post
title: Your Post Title
date: YYYY-MM-DD
categories: ["category1", "category2"]
---
```
3. Write your post content in Markdown (Kramdown syntax)

Posts will be automatically published at `/posts/title-slug/`

## Deployment

This site is automatically deployed to GitHub Pages when you push to the `main` branch.

### Manual Deployment Steps
1. Commit your changes:
```bash
git add .
git commit -m "Your commit message"
```

2. Push to main branch:
```bash
git push origin main
```

3. GitHub Pages will automatically build and deploy your site
4. Check deployment status in the repository **Settings** → **Pages**

### Troubleshooting Deployment
- If the site doesn't update, check the GitHub Pages build logs
- Ensure the CNAME file is present and contains `mikenoe.com`
- Verify Cloudflare DNS settings point to GitHub Pages nameservers
- Clear your browser cache when testing updates

## Tech Stack

- **Static Site Generator**: Jekyll 4.x with Kramdown
- **Markdown Processor**: Kramdown
- **Plugins**: jemoji, jekyll-seo-tag, jekyll-sitemap, jekyll-feed
- **Syntax Highlighting**: Rouge
- **Hosting**: GitHub Pages (via CNAME)

## Project Structure

```
/
├── all_collections/_posts/     # Blog posts (YYYY-MM-DD-title.md)
├── _layouts/                   # Jemplate layouts
├── _includes/                  # Reusable HTML partials
├── _data/                      # Data files
├── assets/
│   ├── css/                    # SCSS/CSS stylesheets
│   └── images/                 # Image assets
├── _site/                      # Generated site (gitignored)
├── _config.yml                 # Jekyll configuration
├── Gemfile                     # Ruby dependencies
└── CNAME                       # GitHub Pages custom domain
```

## License

Personal website content © Mike Noe. All rights reserved.
