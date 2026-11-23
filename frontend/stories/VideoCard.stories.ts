// One card of the video grid, in each state its badge and thumbnail can take.
import VideoCard from '@/components/VideoCard.svelte';
import { fakeVideo, mount } from './utils';

export default { title: 'Components/VideoCard' };

// The width one grid column gets on a desktop.
const CARD_WIDTH = '320px';

export const Downloaded = {
  name: 'Downloaded',
  render: () => mount(VideoCard, { video: fakeVideo() }, CARD_WIDTH),
};

export const Tracked = {
  name: 'Tracked, long title',
  render: () =>
    mount(
      VideoCard,
      {
        video: fakeVideo({
          title:
            'A considerably longer title that has to wrap over two lines on a narrow video card',
          download_status: 'tracked',
          duration: 3725,
          comment_count: 0,
          thumbnail_url: '/videos/2024-03-01_longer-title/thumbnail.svg',
        }),
      },
      CARD_WIDTH,
    ),
};

export const MetadataOnly = {
  name: 'Metadata only',
  render: () =>
    mount(
      VideoCard,
      {
        video: fakeVideo({
          title: 'Metadata only',
          download_status: 'metadata_only',
          duration: 59,
          view_count: 1500000,
          comment_count: 150,
          thumbnail_url: '/videos/2023-11-20_metadata-only/thumbnail.svg',
        }),
      },
      CARD_WIDTH,
    ),
};

export const NoThumbnail = {
  name: 'Thumbnail missing',
  // A URL that 404s inside the built Storybook, so the card falls back to its placeholder.
  render: () =>
    mount(
      VideoCard,
      {
        video: fakeVideo({
          thumbnail_url: '/videos/no-such-video/thumbnail.svg',
        }),
      },
      CARD_WIDTH,
    ),
};
