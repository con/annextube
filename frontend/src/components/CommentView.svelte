<script lang="ts">
  import type { Comment } from '@/types/models';
  import { formatRelativeTime } from '@/utils/format';

  export let comments: Comment[];
  export let loading: boolean = false;

  // Build comment tree from flat list
  function buildCommentTree(comments: Comment[]): Comment[] {
    const commentMap = new Map<string, Comment & { replies: Comment[] }>();
    const rootComments: (Comment & { replies: Comment[] })[] = [];

    // First pass: create map with replies array
    comments.forEach((comment) => {
      commentMap.set(comment.comment_id, { ...comment, replies: [] });
    });

    // Second pass: build tree structure
    comments.forEach((comment) => {
      const commentWithReplies = commentMap.get(comment.comment_id)!;
      if (comment.parent === 'root') {
        rootComments.push(commentWithReplies);
      } else {
        const parent = commentMap.get(comment.parent);
        if (parent) {
          parent.replies.push(commentWithReplies);
        } else {
          // Parent not found, treat as root
          rootComments.push(commentWithReplies);
        }
      }
    });

    return rootComments;
  }

  $: commentTree = buildCommentTree(comments);
</script>

<div class="comments-section">
  {#if loading}
    <h3>Loading comments...</h3>
    <div class="loading-spinner">
      <div class="spinner"></div>
    </div>
  {:else}
    <h3>{comments.length} Comment{comments.length !== 1 ? 's' : ''}</h3>
    {#if comments.length === 0}
      <p class="no-comments">No comments available for this video.</p>
    {:else}
    <div class="comments-list">
      {#each commentTree as comment}
        <div class="comment">
          <div class="comment-header">
            <span class="author">{comment.author}</span>
            <span class="timestamp">{formatRelativeTime(comment.timestamp)}</span>
          </div>
          <div class="comment-text">{comment.text}</div>
          <div class="comment-meta">
            {#if comment.like_count > 0}
              <span class="likes">👍 {comment.like_count.toLocaleString()}</span>
            {/if}
          </div>

          {#if comment.replies && comment.replies.length > 0}
            <details class="replies-details" open>
              <summary class="replies-summary">
                {comment.replies.length} {comment.replies.length === 1 ? 'reply' : 'replies'}
              </summary>
              <div class="replies">
                {#each comment.replies as reply}
                  <div class="comment reply">
                    <div class="comment-header">
                      <span class="author">{reply.author}</span>
                      <span class="timestamp">{formatRelativeTime(reply.timestamp)}</span>
                    </div>
                    <div class="comment-text">{reply.text}</div>
                    <div class="comment-meta">
                      {#if reply.like_count > 0}
                        <span class="likes">👍 {reply.like_count.toLocaleString()}</span>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            </details>
          {/if}
        </div>
      {/each}
    </div>
    {/if}
  {/if}
</div>

<style>
  .comments-section {
    margin-top: 32px;
  }

  .comments-section h3 {
    font-size: 18px;
    font-weight: 500;
    margin-bottom: 24px;
    color: #030303;
  }

  .loading-spinner {
    display: flex;
    justify-content: center;
    padding: 40px 20px;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #065fd4;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  .no-comments {
    color: #606060;
    padding: 20px;
    text-align: center;
    background: #f9f9f9;
    border-radius: 8px;
  }

  .comments-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .comment {
    padding: 16px 0;
    border-bottom: 1px solid #e0e0e0;
  }

  .comment:last-child {
    border-bottom: none;
  }

  .comment.reply {
    padding: 12px 0;
    border-bottom: none;
  }

  .comment-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .author {
    font-weight: 500;
    font-size: 13px;
    color: #030303;
  }

  .timestamp {
    font-size: 12px;
    color: #606060;
  }

  .comment-text {
    font-size: 14px;
    line-height: 1.6;
    color: #030303;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .comment-meta {
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .likes {
    font-size: 12px;
    color: #606060;
  }

  .replies-details {
    margin-top: 8px;
  }

  .replies-summary {
    font-size: 13px;
    color: #065fd4;
    cursor: pointer;
    user-select: none;
    padding: 4px 0;
    font-weight: 500;
  }

  .replies-summary:hover {
    text-decoration: underline;
  }

  .replies {
    margin-left: 40px;
    margin-top: 12px;
    border-left: 2px solid #e0e0e0;
    padding-left: 16px;
  }

  @media (max-width: 768px) {
    .replies {
      margin-left: 20px;
      padding-left: 12px;
    }
  }
</style>
