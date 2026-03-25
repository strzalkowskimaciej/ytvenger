const form       = document.getElementById('submit-form');
const urlInput   = document.getElementById('url-input');
const jobsList   = document.getElementById('jobs-list');
const formError  = document.getElementById('form-error');
const submitBtn  = document.getElementById('submit-btn');
const queueCount = document.getElementById('queue-count');

const STATUS_LABELS = {
  queued:      { text: 'Queued',      css: 'status-queued'      },
  downloading: { text: 'Downloading', css: 'status-downloading' },
  done:        { text: 'Done',        css: 'status-done'        },
  error:       { text: 'Error',       css: 'status-error'       },
};

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  formError.classList.add('hidden');
  const url = urlInput.value.trim();
  submitBtn.disabled = true;
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
    urlInput.value = '';
    await refreshJobs();
  } catch (err) {
    showError('Network error: ' + err.message);
  } finally {
    submitBtn.disabled = false;
    urlInput.focus();
  }
});

function showError(msg) {
  formError.textContent = msg;
  formError.classList.remove('hidden');
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

function renderJobs(jobs) {
  const active = jobs.filter(j => j.status === 'queued' || j.status === 'downloading').length;
  queueCount.textContent = active ? `(${active} active)` : jobs.length ? `(${jobs.length})` : '';

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
