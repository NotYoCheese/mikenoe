# Blog Post Publishing Automation

Automated workflow for publishing blog posts with Mastodon integration.

## Overview

The `publish_post.py` script automates the manual steps required to publish a blog post with Mastodon comments:

1. **Determines the post URL** based on Jekyll's permalink structure
2. **Posts to Mastodon** with a link to your article
3. **Updates the frontmatter** with Mastodon comment information (host, user, post ID)

## Setup

### 1. Install Dependencies

```bash
pip install pyyaml requests
```

### 2. Get Mastodon API Access Token

1. Go to https://mastodon.social/settings/applications
2. Click "New Application"
3. Fill in the details:
   - **Application name**: "Blog Publisher" (or whatever you prefer)
   - **Scopes**: Check `write:statuses` (needed to post)
4. Click "Submit"
5. Click on your new application name
6. Copy the "Your access token" value

### 3. Configure Access Token

Create a `.env` file in the root of your project:

```bash
# .env
MASTODON_ACCESS_TOKEN=your_token_here
```

**Important**: The `.env` file is already in `.gitignore` to prevent committing your token.

Alternatively, you can set an environment variable:

```bash
export MASTODON_ACCESS_TOKEN=your_token_here
```

### 4. Optional: Update _config.yml

You can add these to your `_config.yml` if you want to customize the defaults:

```yaml
# Mastodon settings
mastodon_host: mastodon.social
mastodon_user: mikenoe
url: https://mikenoe.com
```

## Usage

### Using the Slash Command (Easiest)

In Claude Code, use the slash command:

```
/publish-post
```

Claude will ask which post you want to publish and handle the rest.

### Using the Script Directly

```bash
python3 scripts/publish_post.py all_collections/_posts/2025-12-10-my-post.md
```

### Custom Mastodon Message

You can customize the message posted to Mastodon:

```bash
python3 scripts/publish_post.py all_collections/_posts/2025-12-10-my-post.md "Check out my latest post: {title} {url}"
```

Use `{title}` and `{url}` as placeholders - they'll be replaced with the actual values.

## Workflow

When you run the script:

1. **Reads your post** - Parses frontmatter and content
2. **Generates URL** - Based on your permalink structure
3. **Shows preview** - Displays the Mastodon message
4. **Asks for confirmation** - You confirm before posting
5. **Posts to Mastodon** - Creates the post and gets the ID
6. **Updates frontmatter** - Adds Mastodon fields to your post file

The script will check if the post already has a `mastodon_id` and warn you before posting again.

## Example

```bash
$ python3 scripts/publish_post.py all_collections/_posts/2025-12-10-developer-banned-after-reporting-csam-in-ai-data.md

============================================================
Publishing: 2025-12-10-developer-banned-after-reporting-csam-in-ai-data.md
============================================================

Post URL: https://mikenoe.com/posts/developer-banned-after-reporting-csam-in-ai-data/

Mastodon message:
---
New blog post: Developer Banned After Reporting CSAM in AI Data

https://mikenoe.com/posts/developer-banned-after-reporting-csam-in-ai-data/
---

Post to Mastodon? (Y/n): y
Posting to Mastodon...
✓ Posted to Mastodon: https://mastodon.social/@mikenoe/115703398596119400
✓ Updated all_collections/_posts/2025-12-10-developer-banned-after-reporting-csam-in-ai-data.md with Mastodon information

============================================================
✓ Published successfully!
============================================================

Mastodon post: https://mastodon.social/@mikenoe/115703398596119400
Blog post: https://mikenoe.com/posts/developer-banned-after-reporting-csam-in-ai-data/

Comments will appear at: https://mikenoe.com/posts/developer-banned-after-reporting-csam-in-ai-data/#mastodon-comments
```

## Troubleshooting

### "Mastodon access token not found"

Make sure you've created a `.env` file with your token or set the `MASTODON_ACCESS_TOKEN` environment variable.

### "Failed to post to Mastodon"

- Check that your access token is valid
- Ensure your Mastodon app has `write:statuses` permission
- Check your internet connection

### "No valid frontmatter found"

Make sure your post has YAML frontmatter between `---` delimiters at the top of the file.

## What Gets Added to Frontmatter

The script adds these fields to your post:

```yaml
mastodon_host: mastodon.social
mastodon_user: mikenoe
mastodon_id: 115703398596119400
```

These enable the Mastodon comments section on your blog post.

## Security Notes

- **Never commit** your `.env` file or access token to git
- The `.env` file is already in `.gitignore`
- Access tokens should be kept private like passwords
- If you accidentally commit a token, revoke it immediately at https://mastodon.social/settings/applications
