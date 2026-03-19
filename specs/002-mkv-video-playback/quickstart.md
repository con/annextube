# Quickstart: MKV Video Playback

## What Changed

The annextube web UI now handles MKV playback failures gracefully:

1. **Better error messages**: When your browser can't play an MKV file, you
   see specific guidance (update Firefox, use Chrome, or watch on YouTube)
   instead of a generic error.

2. **YouTube fallback**: The "Watch on YouTube" tab remains available as a
   fallback for any playback issues, with a prominent button in error messages.

## Browser Support Matrix

| Browser | MKV Playback | Notes |
|---------|-------------|-------|
| Chrome/Edge | Native | Always worked |
| Firefox 145+ | Native | MKV support added in Firefox 145 |
| Firefox <145 | YouTube fallback | Error message suggests updating Firefox |
| Safari | YouTube fallback | Safari doesn't support MKV natively |
| Mobile Chrome | Native | Same as desktop |
| iOS Safari | YouTube fallback | Safari doesn't support MKV natively |

## For Archive Maintainers

No changes needed to your archives. The `video.mkv` filename convention
continues to work. The improved playback is entirely in the web UI.

To regenerate the web UI with the improved player:

```bash
annextube generate-web --output-dir /path/to/archive
```

## For Users

If a video doesn't play:

1. **Update your browser** — Firefox 145+ and Chrome both support MKV natively
2. **Try a different browser** — Chrome has the broadest MKV support
3. **Use the YouTube tab** — click "Watch on YouTube" for guaranteed playback
