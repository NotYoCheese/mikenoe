#!/usr/bin/env python3
"""
Automated blog post publishing with Mastodon integration.

This script:
1. Reads a Jekyll blog post file
2. Determines the published URL based on Jekyll's permalink structure
3. Posts to Mastodon with a link to the article
4. Updates the post's frontmatter with Mastodon comment information
"""

import os
import sys
import re
import json
import requests
import yaml
from pathlib import Path
from datetime import datetime


class PostPublisher:
    def __init__(self, post_path, config_path="_config.yml", env_file=".env"):
        self.post_path = Path(post_path)
        self.config_path = Path(config_path)
        self.env_file = Path(env_file)

        if not self.post_path.exists():
            raise FileNotFoundError(f"Post file not found: {post_path}")

        # Load configuration
        self.config = self._load_config()
        self.mastodon_token = self._load_mastodon_token()

        # Mastodon settings from config or defaults
        self.mastodon_host = self.config.get('mastodon_host', 'mastodon.social')
        self.mastodon_user = self.config.get('mastodon_user', 'mikenoe')
        self.site_url = self.config.get('url', 'https://mikenoe.com')

    def _load_config(self):
        """Load Jekyll configuration."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    def _load_mastodon_token(self):
        """Load Mastodon access token from environment or .env file."""
        # Try environment variable first
        token = os.environ.get('MASTODON_ACCESS_TOKEN')

        # Try .env file if no env variable
        if not token and self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    if line.startswith('MASTODON_ACCESS_TOKEN='):
                        token = line.split('=', 1)[1].strip().strip('"\'')
                        break

        if not token:
            raise ValueError(
                "Mastodon access token not found. Please set MASTODON_ACCESS_TOKEN "
                "environment variable or add it to .env file.\n"
                "Get your token at: https://mastodon.social/settings/applications"
            )

        return token

    def _parse_frontmatter(self, content):
        """Parse YAML frontmatter from post content."""
        # Match frontmatter between --- delimiters
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
        if not match:
            raise ValueError("No valid frontmatter found in post")

        frontmatter_text = match.group(1)
        body = match.group(2)

        frontmatter = yaml.safe_load(frontmatter_text)
        return frontmatter, body

    def _generate_post_url(self, frontmatter):
        """Generate the post URL based on Jekyll permalink structure."""
        title = frontmatter.get('title', '')
        date = frontmatter.get('date')

        # Convert title to slug (lowercase, replace spaces with hyphens)
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')

        # Use permalink pattern from config (default: /posts/:title/)
        permalink = self.config.get('defaults', [{}])[0].get('values', {}).get('permalink', '/posts/:title/')

        # Replace permalink variables
        url_path = permalink.replace(':title', slug)

        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')

        url_path = url_path.replace(':year', str(date.year))
        url_path = url_path.replace(':month', f'{date.month:02d}')
        url_path = url_path.replace(':day', f'{date.day:02d}')

        return f"{self.site_url}{url_path}"

    def _post_to_mastodon(self, message):
        """Post a message to Mastodon and return the post ID."""
        api_url = f"https://{self.mastodon_host}/api/v1/statuses"

        headers = {
            'Authorization': f'Bearer {self.mastodon_token}',
            'Content-Type': 'application/json',
        }

        data = {
            'status': message,
            'visibility': 'public',
        }

        print(f"Posting to Mastodon...")
        response = requests.post(api_url, headers=headers, json=data)

        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to post to Mastodon: {response.status_code} - {response.text}")

        post_data = response.json()
        post_id = post_data['id']
        post_url = post_data['url']

        print(f"✓ Posted to Mastodon: {post_url}")
        return post_id

    def _update_frontmatter(self, frontmatter, body, mastodon_id):
        """Update the post file with Mastodon information."""
        # Add Mastodon fields to frontmatter
        frontmatter['mastodon_host'] = self.mastodon_host
        frontmatter['mastodon_user'] = self.mastodon_user
        frontmatter['mastodon_id'] = mastodon_id

        # Reconstruct the file
        frontmatter_text = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
        new_content = f"---\n{frontmatter_text}---\n{body}"

        # Write back to file
        with open(self.post_path, 'w') as f:
            f.write(new_content)

        print(f"✓ Updated {self.post_path} with Mastodon information")

    def publish(self, custom_message=None):
        """Main publish workflow."""
        print(f"\n{'='*60}")
        print(f"Publishing: {self.post_path.name}")
        print(f"{'='*60}\n")

        # Read and parse the post
        with open(self.post_path, 'r') as f:
            content = f.read()

        frontmatter, body = self._parse_frontmatter(content)

        # Check if already published to Mastodon
        if frontmatter.get('mastodon_id'):
            print(f"⚠ Warning: This post already has a Mastodon ID: {frontmatter['mastodon_id']}")
            response = input("Do you want to post again anyway? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return

        # Generate URL
        post_url = self._generate_post_url(frontmatter)
        print(f"Post URL: {post_url}")

        # Create Mastodon message
        title = frontmatter.get('title', 'New post')
        if custom_message:
            message = custom_message.replace('{url}', post_url).replace('{title}', title)
        else:
            message = f"New blog post: {title}\n\n{post_url}"

        print(f"\nMastodon message:\n---\n{message}\n---\n")

        # Confirm before posting
        response = input("Post to Mastodon? (Y/n): ")
        if response.lower() == 'n':
            print("Cancelled.")
            return

        # Post to Mastodon
        mastodon_id = self._post_to_mastodon(message)

        # Update frontmatter
        self._update_frontmatter(frontmatter, body, mastodon_id)

        print(f"\n{'='*60}")
        print("✓ Published successfully!")
        print(f"{'='*60}\n")
        print(f"Mastodon post: https://{self.mastodon_host}/@{self.mastodon_user}/{mastodon_id}")
        print(f"Blog post: {post_url}")
        print(f"\nComments will appear at: {post_url}#mastodon-comments")


def main():
    if len(sys.argv) < 2:
        print("Usage: python publish_post.py <post_file> [custom_message]")
        print("\nExample:")
        print("  python publish_post.py all_collections/_posts/2025-12-10-my-post.md")
        print("  python publish_post.py all_collections/_posts/2025-12-10-my-post.md 'Check out my new post: {title} {url}'")
        sys.exit(1)

    post_file = sys.argv[1]
    custom_message = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        publisher = PostPublisher(post_file)
        publisher.publish(custom_message)
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
