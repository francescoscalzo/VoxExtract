import { FFmpeg } from './vendor/ffmpeg/index.js';

// ---------------------------------------------------------------------------
// i18n (stesse chiavi di vox_extract.py, più quelle specifiche del web)
// ---------------------------------------------------------------------------
const TRANSLATIONS = {
  it: {
    app_subtitle: 'Estrai audio dai tuoi video con stile',
    drop_video_here: 'Trascina qui i file video',
    drop_hint: 'oppure clicca per sceglierli',
    format: 'Formato',
    quality: 'Qualità',
    quality_low: 'Bassa (128 kbps)',
    quality_medium: 'Media (192 kbps)',
    quality_high: 'Alta (256 kbps)',
    quality_best: 'Massima (320 kbps)',
    extract_audio: '⚡ ESTRAI AUDIO ⚡',
    extract_n: '⚡ ESTRAI AUDIO ({n} file) ⚡',
    cancel: '✕ ANNULLA',
    engine_loading: 'Caricamento motore audio… (solo la prima volta, ~30 MB)',
    engine_ready: 'Pronto · funziona anche offline',
    engine_error: 'Impossibile caricare il motore audio: {msg}',
    status_waiting: 'In attesa',
    status_running: '{percent}%',
    status_running_nodur: 'In corso…',
    status_done: 'Completato',
    status_failed: 'Errore',
    status_cancelled: 'Annullato',
    download: '💾 Scarica {name}',
    error_video_no_audio: 'Il file non contiene una traccia audio',
    error_extraction: "Errore durante l'estrazione dell'audio",
    install_app: '⬇ Installa come app',
    install_hint_safari: "Per installarla: menu File → Aggiungi al Dock (Safari su Mac) oppure Condividi → Aggiungi a Home (iPhone/iPad).",
    privacy: 'I file non lasciano mai il tuo computer: tutto avviene nel browser.',
  },
  en: {
    app_subtitle: 'Extract audio from your videos with style',
    drop_video_here: 'Drop video files here',
    drop_hint: 'or click to choose them',
    format: 'Format',
    quality: 'Quality',
    quality_low: 'Low (128 kbps)',
    quality_medium: 'Medium (192 kbps)',
    quality_high: 'High (256 kbps)',
    quality_best: 'Best (320 kbps)',
    extract_audio: '⚡ EXTRACT AUDIO ⚡',
    extract_n: '⚡ EXTRACT AUDIO ({n} files) ⚡',
    cancel: '✕ CANCEL',
    engine_loading: 'Loading audio engine… (first time only, ~30 MB)',
    engine_ready: 'Ready · works offline too',
    engine_error: 'Could not load the audio engine: {msg}',
    status_waiting: 'Waiting',
    status_running: '{percent}%',
    status_running_nodur: 'Working…',
    status_done: 'Done',
    status_failed: 'Error',
    status_cancelled: 'Cancelled',
    download: '💾 Download {name}',
    error_video_no_audio: 'The file does not contain an audio track',
    error_extraction: 'Error during audio extraction',
    install_app: '⬇ Install as app',
    install_hint_safari: 'To install: File menu → Add to Dock (Safari on Mac) or Share → Add to Home Screen (iPhone/iPad).',
    privacy: 'Your files never leave your computer: everything runs in the browser.',
  },
};

const LANG_KEY = 'voxextract.lang';
let lang = (() => {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved && TRANSLATIONS[saved]) return saved;
  } catch {}
  return navigator.language?.toLowerCase().startsWith('it') ? 'it' : 'en';
})();

function t(key, params = {}) {
  const text = TRANSLATIONS[lang][key] ?? TRANSLATIONS.it[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, k) => params[k] ?? '');
}

// ---------------------------------------------------------------------------
// Configurazione (identica a QUALITY_PRESETS / AUDIO_FORMATS in vox_extract.py)
// ---------------------------------------------------------------------------
const QUALITY_PRESETS = { low: '128k', medium: '192k', high: '256k', best: '320k' };

const AUDIO_FORMATS = {
  MP3: { extension: 'mp3', muxer: 'mp3', codec: 'libmp3lame', mime: 'audio/mpeg', lossless: false },
  AAC: { extension: 'aac', muxer: 'adts', codec: 'aac', mime: 'audio/aac', lossless: false },
  FLAC: { extension: 'flac', muxer: 'flac', codec: 'flac', mime: 'audio/flac', lossless: true },
  WAV: { extension: 'wav', muxer: 'wav', codec: 'pcm_s16le', mime: 'audio/wav', lossless: true },
};

// ---------------------------------------------------------------------------
// DOM
// ---------------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const els = {
  drop: $('#drop'),
  fileInput: $('#file-input'),
  format: $('#format'),
  quality: $('#quality'),
  qualityField: $('#quality-field'),
  extract: $('#extract'),
  extractLabel: $('#extract-label'),
  engine: $('#engine'),
  queueCard: $('#queue-card'),
  queue: $('#queue'),
  install: $('#install'),
  installHint: $('#install-hint'),
  itemTpl: $('#item-tpl'),
};

/** @type {{file: File, el: HTMLElement, state: string, url?: string}[]} */
let jobs = [];
let running = false;
let cancelRequested = false;
let engineState = 'loading'; // loading | ready | error
let engineError = '';

// ---------------------------------------------------------------------------
// FFmpeg engine
// ---------------------------------------------------------------------------
let ffmpeg = null;
let logHandler = null;

async function loadEngine() {
  engineState = 'loading';
  renderEngine();
  try {
    ffmpeg = new FFmpeg();
    ffmpeg.on('log', ({ message }) => logHandler?.(message));
    await ffmpeg.load({
      coreURL: new URL('./vendor/core/ffmpeg-core.js', location.href).href,
      wasmURL: new URL('./vendor/core/ffmpeg-core.wasm', location.href).href,
    });
    engineState = 'ready';
  } catch (err) {
    console.error(err);
    engineState = 'error';
    engineError = err?.message || String(err);
  }
  renderEngine();
  renderExtractButton();
}

const DURATION_RE = /Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)/;
const TIME_RE = /time=\s*(\d+):(\d+):(\d+(?:\.\d+)?)/;
const toSeconds = (m) => (+m[1]) * 3600 + (+m[2]) * 60 + parseFloat(m[3]);

async function extractOne(job, index, formatKey, qualityKey) {
  const fmt = AUDIO_FORMATS[formatKey];
  const inDir = `/in${index}`;
  const inPath = `${inDir}/${job.file.name}`;
  const outPath = `/out${index}.${fmt.extension}`;

  let duration = 0;
  let noAudio = false;
  logHandler = (msg) => {
    if (!duration) {
      const d = msg.match(DURATION_RE);
      if (d) duration = toSeconds(d);
    }
    if (/matches no streams|does not contain any stream/i.test(msg)) noAudio = true;
    const tm = msg.match(TIME_RE);
    if (tm) {
      setJobProgress(job, duration ? Math.min(99, (toSeconds(tm) / duration) * 100) : null);
    }
  };

  // WORKERFS legge il File direttamente, senza copiarlo in memoria: regge file grandi.
  await ffmpeg.createDir(inDir);
  await ffmpeg.mount('WORKERFS', { files: [job.file] }, inDir);

  const args = ['-i', inPath, '-vn', '-map', '0:a:0', '-c:a', fmt.codec];
  if (!fmt.lossless) args.push('-b:a', QUALITY_PRESETS[qualityKey]);
  args.push('-f', fmt.muxer, '-y', outPath);

  try {
    const code = await ffmpeg.exec(args);
    if (code !== 0) throw new Error(noAudio ? t('error_video_no_audio') : t('error_extraction'));
    const data = await ffmpeg.readFile(outPath);
    await ffmpeg.deleteFile(outPath).catch(() => {});
    return new Blob([data], { type: fmt.mime });
  } finally {
    logHandler = null;
    if (!cancelRequested) {
      await ffmpeg.unmount(inDir).catch(() => {});
      await ffmpeg.deleteDir(inDir).catch(() => {});
    }
  }
}

// ---------------------------------------------------------------------------
// Queue
// ---------------------------------------------------------------------------
function addFiles(fileList) {
  if (running) return;
  const files = [...fileList].filter((f) => f.size > 0);
  if (!files.length) return;
  // Una nuova selezione sostituisce la coda precedente.
  for (const job of jobs) if (job.url) URL.revokeObjectURL(job.url);
  jobs = files.map((file) => {
    const el = els.itemTpl.content.firstElementChild.cloneNode(true);
    el.querySelector('.item-name').textContent = file.name;
    el.querySelector('.item-name').title = file.name;
    return { file, el, state: 'waiting' };
  });
  els.queue.replaceChildren(...jobs.map((j) => j.el));
  els.queueCard.hidden = false;
  jobs.forEach(renderJob);
  renderExtractButton();
}

function setJobProgress(job, percent) {
  job.percent = percent;
  renderJob(job);
}

function renderJob(job) {
  const { el, state } = job;
  el.classList.toggle('done', state === 'done');
  el.classList.toggle('failed', state === 'failed' || state === 'cancelled');
  const status = el.querySelector('.item-status');
  const fill = el.querySelector('.bar-fill');
  const actions = el.querySelector('.item-actions');

  if (state === 'waiting') {
    status.textContent = t('status_waiting');
    fill.style.width = '0';
  } else if (state === 'running') {
    status.textContent = job.percent == null
      ? t('status_running_nodur')
      : t('status_running', { percent: Math.round(job.percent) });
    fill.style.width = `${job.percent ?? 5}%`;
  } else if (state === 'done') {
    status.textContent = t('status_done');
    fill.style.width = '100%';
  } else if (state === 'failed') {
    status.textContent = t('status_failed');
    fill.style.width = '100%';
  } else if (state === 'cancelled') {
    status.textContent = t('status_cancelled');
  }

  actions.replaceChildren();
  if (state === 'done' && job.url) {
    const a = document.createElement('a');
    a.className = 'download';
    a.href = job.url;
    a.download = job.outName;
    a.textContent = t('download', { name: job.outName });
    actions.append(a);
  } else if (state === 'failed' && job.error) {
    const p = document.createElement('p');
    p.className = 'item-error';
    p.textContent = job.error;
    actions.append(p);
  }
}

async function runQueue() {
  running = true;
  cancelRequested = false;
  renderExtractButton();
  setOptionsDisabled(true);

  const formatKey = els.format.value;
  const qualityKey = els.quality.value;
  const ext = AUDIO_FORMATS[formatKey].extension;

  for (const [i, job] of jobs.entries()) {
    if (job.state === 'done') continue;
    if (cancelRequested) { job.state = 'cancelled'; renderJob(job); continue; }
    job.state = 'running';
    job.percent = 0;
    job.error = undefined;
    renderJob(job);
    try {
      const blob = await extractOne(job, i, formatKey, qualityKey);
      job.outName = job.file.name.replace(/\.[^./\\]+$/, '') + '.' + ext;
      job.url = URL.createObjectURL(blob);
      job.state = 'done';
      if (jobs.length === 1) triggerDownload(job);
    } catch (err) {
      if (cancelRequested) {
        job.state = 'cancelled';
      } else {
        console.error(err);
        job.state = 'failed';
        job.error = err?.message || String(err);
      }
    }
    renderJob(job);
  }

  running = false;
  setOptionsDisabled(false);
  renderExtractButton();
}

function triggerDownload(job) {
  const a = document.createElement('a');
  a.href = job.url;
  a.download = job.outName;
  document.body.append(a);
  a.click();
  a.remove();
}

async function cancel() {
  if (!running) return;
  cancelRequested = true;
  // terminate() interrompe subito il worker; il motore va poi ricaricato.
  ffmpeg.terminate();
  await loadEngine();
}

// ---------------------------------------------------------------------------
// UI rendering
// ---------------------------------------------------------------------------
function applyI18n() {
  document.documentElement.lang = lang;
  for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = t(el.dataset.i18n);
  for (const b of document.querySelectorAll('.lang-btn')) b.classList.toggle('active', b.dataset.lang === lang);
  renderEngine();
  renderExtractButton();
  jobs.forEach(renderJob);
  renderInstallHint();
}

function renderEngine() {
  els.engine.classList.toggle('error', engineState === 'error');
  els.engine.textContent =
    engineState === 'loading' ? t('engine_loading')
    : engineState === 'ready' ? t('engine_ready')
    : t('engine_error', { msg: engineError });
}

function renderExtractButton() {
  const pending = jobs.filter((j) => j.state !== 'done').length;
  if (running) {
    els.extract.classList.add('cancel');
    els.extract.disabled = engineState !== 'ready';
    els.extractLabel.textContent = t('cancel');
    return;
  }
  els.extract.classList.remove('cancel');
  els.extract.disabled = engineState !== 'ready' || pending === 0;
  els.extractLabel.textContent = pending > 1 ? t('extract_n', { n: pending }) : t('extract_audio');
}

function setOptionsDisabled(disabled) {
  els.format.disabled = disabled;
  els.quality.disabled = disabled || AUDIO_FORMATS[els.format.value].lossless;
  els.qualityField.classList.toggle('disabled', els.quality.disabled);
  els.drop.style.pointerEvents = disabled ? 'none' : '';
  els.drop.style.opacity = disabled ? '.5' : '';
}

// ---------------------------------------------------------------------------
// Install (PWA)
// ---------------------------------------------------------------------------
let deferredPrompt = null;
const isStandalone = () =>
  matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
const isSafari = /^((?!chrome|android|crios|fxios|edg).)*safari/i.test(navigator.userAgent);

function renderInstallHint() {
  const showSafari = isSafari && !isStandalone();
  els.installHint.hidden = !showSafari;
  if (showSafari) els.installHint.textContent = t('install_hint_safari');
}

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  els.install.hidden = false;
});
window.addEventListener('appinstalled', () => {
  deferredPrompt = null;
  els.install.hidden = true;
});
els.install.addEventListener('click', async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  els.install.hidden = true;
});

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------
els.fileInput.addEventListener('change', () => {
  addFiles(els.fileInput.files);
  els.fileInput.value = '';
});

for (const type of ['dragenter', 'dragover']) {
  els.drop.addEventListener(type, (e) => { e.preventDefault(); els.drop.classList.add('over'); });
}
for (const type of ['dragleave', 'drop']) {
  els.drop.addEventListener(type, () => els.drop.classList.remove('over'));
}
els.drop.addEventListener('drop', (e) => {
  e.preventDefault();
  addFiles(e.dataTransfer.files);
});
// Evita che un file lasciato fuori dalla drop zone venga aperto dal browser.
window.addEventListener('dragover', (e) => e.preventDefault());
window.addEventListener('drop', (e) => e.preventDefault());

els.format.addEventListener('change', () => {
  setOptionsDisabled(false);
  // Cambiare formato rende di nuovo estraibili i file già fatti.
  for (const job of jobs) {
    if (job.url) URL.revokeObjectURL(job.url);
    job.url = undefined;
    job.state = 'waiting';
    renderJob(job);
  }
  renderExtractButton();
});
els.quality.addEventListener('change', () => {
  for (const job of jobs) {
    if (job.url) URL.revokeObjectURL(job.url);
    job.url = undefined;
    job.state = 'waiting';
    renderJob(job);
  }
  renderExtractButton();
});

els.extract.addEventListener('click', () => (running ? cancel() : runQueue()));

for (const b of document.querySelectorAll('.lang-btn')) {
  b.addEventListener('click', () => {
    lang = b.dataset.lang;
    try { localStorage.setItem(LANG_KEY, lang); } catch {}
    applyI18n();
  });
}

// App installata: "Apri con VoxExtract" dal file manager (Chrome/Edge desktop).
if ('launchQueue' in window) {
  window.launchQueue.setConsumer(async ({ files }) => {
    if (!files?.length) return;
    addFiles(await Promise.all(files.map((h) => h.getFile())));
  });
}

window.addEventListener('beforeunload', (e) => {
  if (running) e.preventDefault();
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js').catch((err) => console.warn('SW non registrato', err));
}

applyI18n();
setOptionsDisabled(false);
loadEngine();
