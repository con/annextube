// The comment thread under a video.
import CommentView from '@/components/CommentView.svelte';
import { fakeComment, mount } from './utils';

export default { title: 'Components/CommentView' };

// The width of the video detail column.
const COLUMN_WIDTH = '900px';

const comments = [
  fakeComment('c1', 'A top-level fixture comment.'),
  fakeComment('c2', 'A reply to it.', 'c1', { like_count: 3 }),
  fakeComment(
    'c3',
    'A second top-level comment, long enough to wrap on a phone: lorem ipsum dolor sit amet, consectetur adipiscing elit.',
    'root',
    { like_count: 0 },
  ),
];

export const Threaded = {
  name: 'Threaded',
  render: () =>
    mount(
      CommentView,
      { comments, commentCount: comments.length },
      COLUMN_WIDTH,
    ),
};

export const None = {
  name: 'No comments',
  render: () =>
    mount(CommentView, { comments: [], commentCount: 0 }, COLUMN_WIDTH),
};

export const NotFetched = {
  name: 'Comments not fetched',
  render: () =>
    mount(CommentView, { comments: [], commentCount: 150 }, COLUMN_WIDTH),
};

export const Loading = {
  name: 'Loading',
  render: () =>
    mount(CommentView, { comments: [], loading: true }, COLUMN_WIDTH),
};
