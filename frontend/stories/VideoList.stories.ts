// The video grid with its result count, and what stands in for it while loading or on failure.
import VideoList from '@/components/VideoList.svelte';
import { fakeVideo, mount } from './utils';

export default { title: 'Components/VideoList' };

const videos = [
  fakeVideo(),
  fakeVideo({
    video_id: 'STORY000002',
    title:
      'A considerably longer title that has to wrap over two lines on a narrow video card',
    download_status: 'tracked',
    thumbnail_url: '/videos/2024-03-01_longer-title/thumbnail.svg',
  }),
  fakeVideo({
    video_id: 'STORY000003',
    title: 'Metadata only',
    download_status: 'metadata_only',
    thumbnail_url: '/videos/2023-11-20_metadata-only/thumbnail.svg',
  }),
];

export const Videos = {
  name: 'Videos',
  render: () => mount(VideoList, { videos, totalVideos: videos.length }),
};

export const Filtered = {
  name: 'Filtered (1 of 3)',
  render: () =>
    mount(VideoList, {
      videos: videos.slice(0, 1),
      totalVideos: videos.length,
    }),
};

export const Empty = {
  name: 'No videos',
  render: () => mount(VideoList, { videos: [], totalVideos: 0 }),
};

export const Loading = {
  name: 'Loading',
  render: () => mount(VideoList, { videos: [], loading: true }),
};

export const LoadError = {
  name: 'Load error',
  render: () =>
    mount(VideoList, {
      videos: [],
      error: 'Failed to load videos.tsv: File not found',
    }),
};
