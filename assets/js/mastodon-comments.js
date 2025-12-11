document.addEventListener('DOMContentLoaded', function() {
  const loadButton = document.getElementById('load-comments');

  if (!loadButton) return;

  loadButton.addEventListener('click', function() {
    loadButton.disabled = true;
    loadButton.textContent = 'Loading...';
    loadComments();
  });
});

async function loadComments() {
  const commentsContainer = document.getElementById('mastodon-comments-list');

  try {
    const response = await fetch(
      `https://${mastodonHost}/api/v1/statuses/${mastodonId}/context`
    );

    if (!response.ok) {
      throw new Error('Failed to fetch comments');
    }

    const data = await response.json();
    const descendants = data.descendants;

    if (descendants.length === 0) {
      commentsContainer.innerHTML = '<p class="no-comments">No comments yet. Be the first to reply on Mastodon!</p>';
      return;
    }

    // Sort comments by creation date
    descendants.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

    commentsContainer.innerHTML = descendants.map(comment => {
      return renderComment(comment);
    }).join('');

  } catch (error) {
    console.error('Error loading comments:', error);
    commentsContainer.innerHTML = '<p class="error-message">Failed to load comments. Please try again later.</p>';
  }
}

function renderComment(comment) {
  const author = comment.account;
  const isOP = author.acct === mastodonUser || author.acct === `${mastodonUser}@${mastodonHost}`;

  // Sanitize the content using DOMPurify
  const sanitizedContent = DOMPurify.sanitize(comment.content);

  // Format the date
  const date = new Date(comment.created_at);
  const formattedDate = date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });

  return `
    <div class="mastodon-comment ${isOP ? 'author-comment' : ''}">
      <div class="comment-header">
        <img src="${escapeHtml(author.avatar)}" alt="${escapeHtml(author.display_name)}" class="comment-avatar" />
        <div class="comment-author-info">
          <a href="${escapeHtml(author.url)}" target="_blank" class="comment-author">
            <strong>${escapeHtml(author.display_name)}</strong>
            ${isOP ? '<span class="author-badge">Author</span>' : ''}
          </a>
          <span class="comment-username">@${escapeHtml(author.acct)}</span>
        </div>
        <a href="${escapeHtml(comment.url)}" target="_blank" class="comment-date">${formattedDate}</a>
      </div>
      <div class="comment-content">
        ${sanitizedContent}
      </div>
      <div class="comment-footer">
        <a href="${escapeHtml(comment.url)}" target="_blank" class="comment-link">View on Mastodon</a>
        ${comment.replies_count > 0 ? `<span class="replies-count">${comment.replies_count} ${comment.replies_count === 1 ? 'reply' : 'replies'}</span>` : ''}
      </div>
    </div>
  `;
}

function escapeHtml(unsafe) {
  if (!unsafe) return '';
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
