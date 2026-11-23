// The channel cards a multi-channel collection opens on.
import ChannelList from '@/components/ChannelList.svelte';
import { fakeChannel, mount } from './utils';

export default { title: 'Components/ChannelList' };

const channels = [
  fakeChannel(),
  fakeChannel({
    channel_id: 'UCFIXTURE02',
    name: 'Second Fixture Channel',
    custom_url: '@SecondFixtureChannel',
    description:
      'A second channel, with a description long enough to be clamped on a channel card: lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor.',
    subscriber_count: 2500,
    channel_dir: 'ch-beta',
    archive_stats: {
      total_videos_archived: 12,
      first_video_date: '2021-03-01',
      last_video_date: '2024-05-15',
      total_duration_seconds: 7200,
      total_size_bytes: 104857600,
    },
  }),
];

export const Channels = {
  name: 'Channels',
  render: () => mount(ChannelList, { channels }),
};

export const Empty = {
  name: 'No channels',
  render: () => mount(ChannelList, { channels: [] }),
};

export const Loading = {
  name: 'Loading',
  render: () => mount(ChannelList, { channels: [], loading: true }),
};

export const LoadError = {
  name: 'Load error',
  render: () =>
    mount(ChannelList, {
      channels: [],
      error: 'Failed to load channels.tsv: File not found',
    }),
};
