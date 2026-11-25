# Vendored third-party files

Copied unmodified from npm so the app works offline and same-origin (no CDN, no COOP/COEP headers needed).

| Path | Package | Version | License | Source |
|---|---|---|---|---|
| `ffmpeg/` | `@ffmpeg/ffmpeg` (`dist/esm`) | 0.12.15 | MIT | https://github.com/ffmpegwasm/ffmpeg.wasm |
| `core/` | `@ffmpeg/core` (`dist/esm`, single-thread) | 0.12.10 | GPL-2.0-or-later | https://github.com/ffmpegwasm/ffmpeg.wasm/tree/main/build — FFmpeg: https://ffmpeg.org |

`ffmpeg-core.wasm` is a build of FFmpeg and bundled libraries (incl. LAME) distributed under the GPL; corresponding source is available at the links above.

To update:

```bash
npm pack @ffmpeg/ffmpeg@<ver> @ffmpeg/core@<ver>
# extract, then copy package/dist/esm/*.js -> ffmpeg/ and ffmpeg-core.{js,wasm} -> core/
```

After updating, bump `VERSION` in `../sw.js` so installed clients refresh their cache.
