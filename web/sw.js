// Service worker: mette in cache l'intera app (incluso il motore ffmpeg.wasm)
// così da funzionare offline dopo la prima apertura.
// Incrementa VERSION a ogni rilascio per forzare l'aggiornamento della cache.
const VERSION = 'v1';
const CACHE = `voxextract-${VERSION}`;

const ASSETS = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-512.png',
  './icons/apple-touch-icon.png',
  './vendor/ffmpeg/index.js',
  './vendor/ffmpeg/classes.js',
  './vendor/ffmpeg/const.js',
  './vendor/ffmpeg/errors.js',
  './vendor/ffmpeg/types.js',
  './vendor/ffmpeg/utils.js',
  './vendor/ffmpeg/worker.js',
  './vendor/core/ffmpeg-core.js',
  './vendor/core/ffmpeg-core.wasm',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET' || new URL(request.url).origin !== location.origin) return;
  event.respondWith(
    caches.match(request, { ignoreSearch: true }).then((hit) => hit || fetch(request))
  );
});
