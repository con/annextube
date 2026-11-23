import type { ComponentProps, ComponentType, SvelteComponent } from 'svelte';
import type { Channel, Comment, Video } from '@/types/models';

/**
 * Mounts a real Svelte component for a story. Storybook runs under its HTML framework here (see
 * .storybook/main.ts), so a story's `render` returns an element, and this is what puts the
 * component in it. `maxWidth` centers it at a realistic width, the way the page shell would.
 */
export function mount<C extends SvelteComponent>(
  component: ComponentType<C>,
  props: ComponentProps<C>,
  maxWidth = '1400px',
): HTMLDivElement {
  const wrapper = document.createElement('div');
  wrapper.style.maxWidth = maxWidth;
  wrapper.style.margin = '1.5rem auto';
  new component({ target: wrapper, props });
  return wrapper;
}

// Fixed, obviously fake inputs, so every capture comes out alike. Thumbnails are the snapshot
// suite's fixture files, mounted at /videos by .storybook/main.ts.

export function fakeVideo(overrides: Partial<Video> = {}): Video {
  return {
    video_id: 'STORY000001',
    title: 'Introduction to the fixture archive',
    channel_id: 'UCFIXTURE01',
    channel_name: 'Fixture Channel',
    published_at: '2024-01-15T12:00:00Z',
    duration: 754,
    view_count: 12345,
    like_count: 321,
    comment_count: 3,
    thumbnail_url: '/videos/2024-01-15_introduction/thumbnail.svg',
    license: 'standard',
    privacy_status: 'public',
    availability: 'public',
    tags: [],
    categories: [],
    captions_available: [],
    has_auto_captions: false,
    file_path: '2024-01-15_introduction',
    download_status: 'downloaded',
    source_url: 'https://www.youtube.com/watch?v=STORY000001',
    fetched_at: '2024-06-01T00:00:00Z',
    updated_at: '2024-06-01T00:00:00Z',
    ...overrides,
  };
}

export function fakeChannel(overrides: Partial<Channel> = {}): Channel {
  return {
    channel_id: 'UCFIXTURE01',
    name: 'Fixture Channel',
    description: 'The first channel of the snapshot fixture collection',
    custom_url: '@FixtureChannel',
    subscriber_count: 50000,
    video_count: 100,
    avatar_url: '',
    videos: [],
    playlists: [],
    last_sync: '2024-06-15T00:00:00Z',
    created_at: '2019-01-01T00:00:00Z',
    fetched_at: '2024-06-15T00:00:00Z',
    archive_stats: {
      total_videos_archived: 95,
      first_video_date: '2020-01-01',
      last_video_date: '2024-06-01',
      total_duration_seconds: 360000,
      total_size_bytes: 5368709120,
    },
    channel_dir: 'ch-alpha',
    ...overrides,
  };
}

// `parent` is what comments.json carries and CommentView threads by ('root' for a top-level
// comment); the generated Comment type does not list it.
export function fakeComment(
  id: string,
  text: string,
  parent = 'root',
  overrides: Partial<Comment> = {},
): Comment {
  return {
    comment_id: id,
    video_id: 'STORY000001',
    author: `@fixture-${id}`,
    author_channel_id: `UCAUTHOR-${id}`,
    text,
    timestamp: '2024-01-16T08:00:00Z',
    like_count: 12,
    parent,
    reply_count: 0,
    fetched_at: '2024-06-01T00:00:00Z',
    ...overrides,
  } as Comment;
}
