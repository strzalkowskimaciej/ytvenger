const form            = document.getElementById('submit-form');
const urlInput        = document.getElementById('url-input');
const jobsList        = document.getElementById('jobs-list');
const formError       = document.getElementById('form-error');
const submitBtn       = document.getElementById('submit-btn');
const queueCount      = document.getElementById('queue-count');
const cancelAllBtn    = document.getElementById('cancel-all-btn');
const playlistConfirm = document.getElementById('playlist-confirm');
const confirmMsg      = document.getElementById('playlist-confirm-msg');
const btnPlaylist     = document.getElementById('btn-playlist');
const btnSingle       = document.getElementById('btn-single');
const btnCancel       = document.getElementById('btn-cancel');

const STATUS_LABELS = {
  queued:      { text: 'Queued',      css: 'status-queued'      },
  downloading: { text: 'Downloading', css: 'status-downloading' },
  done:        { text: 'Done',        css: 'status-done'        },
  error:       { text: 'Error',       css: 'status-error'       },
  cancelled:   { text: 'Cancelled',   css: 'status-cancelled'   },
};

function isPlaylistUrl(url) {
  return url.includes('list=');
}

function hasSingleVideo(url) {
  try {
    const v = new URL(url).searchParams.get('v');
    return !!v;
  } catch { return false; }
}

function singleVideoUrl(url) {
  try {
    const v = new URL(url).searchParams.get('v');
    return v ? `https://www.youtube.com/watch?v=${v}` : url;
  } catch { return url; }
}

function hideConfirm() {
  playlistConfirm.classList.add('hidden');
  btnSingle.classList.remove('hidden');
}

// --- Submit form ---
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  formError.textContent = '';
  formError.className = 'hidden';
  hideConfirm();

  const url = urlInput.value.trim();

  if (isPlaylistUrl(url)) {
    confirmMsg.textContent = 'This URL contains a playlist. What would you like to download?';
    btnSingle.classList.toggle('hidden', !hasSingleVideo(url));
    playlistConfirm.classList.remove('hidden');
    return; // wait for user choice
  }

  await submitUrl(url);
});

// --- Playlist confirm buttons ---
btnPlaylist.addEventListener('click', async () => {
  hideConfirm();
  await submitUrl(urlInput.value.trim(), false);
});

btnSingle.addEventListener('click', async () => {
  hideConfirm();
  await submitUrl(singleVideoUrl(urlInput.value.trim()), true);
});

btnCancel.addEventListener('click', () => {
  hideConfirm();
  urlInput.focus();
});

// --- Core submit logic ---
async function submitUrl(url, isSingle = true) {
  formError.textContent = '';
  formError.className = 'hidden';
  submitBtn.disabled = true;
  submitBtn.textContent = isSingle ? 'Adding…' : 'Loading playlist…';
  try {
    const res = await fetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    if (!res.ok) {
      const data = await res.json();
      showError(data.detail || 'Submission failed');
      return;
    }
    const jobs = await res.json();
    urlInput.value = '';
    if (jobs.length > 1) {
      showInfo(`Added ${jobs.length} videos to queue.`);
    }
    await refreshJobs();
  } catch (err) {
    showError('Network error: ' + err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Add to Queue';
    urlInput.focus();
  }
}

function showError(msg) {
  formError.className = 'error-msg';
  formError.textContent = msg;
}

function showInfo(msg) {
  formError.className = 'info-msg';
  formError.textContent = msg;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString();
}

cancelAllBtn.addEventListener('click', async () => {
  cancelAllBtn.disabled = true;
  try {
    await fetch('/api/jobs/cancel-all', { method: 'POST' });
    await refreshJobs();
  } finally {
    cancelAllBtn.disabled = false;
  }
});

function renderJobs(jobs) {
  const active = jobs.filter(j => j.status === 'queued' || j.status === 'downloading').length;
  queueCount.textContent = active ? `(${active} active)` : jobs.length ? `(${jobs.length})` : '';
  cancelAllBtn.classList.toggle('hidden', active === 0);

  if (!jobs.length) {
    jobsList.innerHTML = '<p class="empty-state">No jobs yet. Paste a URL above to get started.</p>';
    return;
  }

  jobsList.innerHTML = jobs.map(job => {
    const label = STATUS_LABELS[job.status] || { text: job.status, css: '' };
    const title = job.title || job.url;
    const spinner = job.status === 'downloading' ? '<span class="spinner"></span>' : '';
    const downloadBtn = job.status === 'done' && job.filename
      ? `<a class="download-btn" href="/downloads/${job.filename.split('/').map(encodeURIComponent).join('/')}" download="${encodeURIComponent(job.filename.split('/').pop())}">Download MP3</a>`
      : '';
    const errorMsg = job.status === 'error'
      ? `<div class="job-error">${escapeHtml(job.error || 'Unknown error')}</div>`
      : '';

    return `
      <div class="job-card ${label.css}">
        <div class="job-title">${escapeHtml(title)}</div>
        <div class="job-meta">
          <span class="status-badge">${spinner}${label.text}</span>
          <span class="job-time">${formatTime(job.created_at)}</span>
        </div>
        ${errorMsg}
        ${downloadBtn}
      </div>`;
  }).join('');
}

async function refreshJobs() {
  try {
    const res = await fetch('/api/jobs');
    if (!res.ok) return;
    const jobs = await res.json();
    renderJobs(jobs);
  } catch (_) {}
}

refreshJobs();
setInterval(refreshJobs, 3000);
