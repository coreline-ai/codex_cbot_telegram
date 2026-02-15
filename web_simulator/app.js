const chatEl = document.getElementById('chat');
const statusEl = document.getElementById('status');
const formEl = document.getElementById('composer');
const inputEl = document.getElementById('msgInput');
const debugLogEl = document.getElementById('debugLog');
const debugMetaEl = document.getElementById('debugMeta');
const copyDebugBtnEl = document.getElementById('copyDebugBtn');
const clearDebugBtnEl = document.getElementById('clearDebugBtn');
const scrollDebugUpBtnEl = document.getElementById('scrollDebugUpBtn');
const scrollDebugDownBtnEl = document.getElementById('scrollDebugDownBtn');
const retriggerBtnEl = document.getElementById('retriggerBtn');
const testPingBtnEl = document.getElementById('testPingBtn');
const stopWorkerBtnEl = document.getElementById('stopWorkerBtn');
const controlStatusEl = document.getElementById('controlStatus');

let lastSignature = '';
let lastLogSignature = '';
let debugLines = [];

const DEBUG_MAX_LINES = 2000;

function isNearBottom(el, threshold = 24) {
  const remaining = el.scrollHeight - el.scrollTop - el.clientHeight;
  return remaining <= threshold;
}

function findOverlap(prevLines, nextLines) {
  const max = Math.min(prevLines.length, nextLines.length);
  for (let size = max; size > 0; size -= 1) {
    let matched = true;
    for (let i = 0; i < size; i += 1) {
      if (prevLines[prevLines.length - size + i] !== nextLines[i]) {
        matched = false;
        break;
      }
    }
    if (matched) return size;
  }
  return 0;
}

function setDebugContent(lines, keepBottom) {
  debugLines = lines.slice(-DEBUG_MAX_LINES);
  debugLogEl.textContent = debugLines.length ? debugLines.join('\n') : '로그 없음';
  if (keepBottom) {
    debugLogEl.scrollTop = debugLogEl.scrollHeight;
  }
}

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function messageToHtml(msg) {
  const dirClass = msg.direction === 'in' ? 'in' : 'out';
  const body = [];

  if (msg.kind === 'photo' && msg.file_url) {
    if (msg.caption) body.push(`<div>${escapeHtml(msg.caption)}</div>`);
    body.push(`<a href="${msg.file_url}" target="_blank" rel="noreferrer"><img class="preview" src="${msg.file_url}" alt="photo" /></a>`);
  } else if (msg.kind === 'document' && msg.file_url) {
    if (msg.caption) body.push(`<div>${escapeHtml(msg.caption)}</div>`);
    body.push(`<a class="file-link" href="${msg.file_url}" target="_blank" rel="noreferrer">파일 열기: ${escapeHtml(msg.file_path || 'document')}</a>`);
  } else {
    body.push(`<div>${escapeHtml(msg.text || '')}</div>`);
  }

  const meta = [msg.timestamp, msg.kind].filter(Boolean).join(' • ');
  return `<article class="bubble ${dirClass}">${body.join('')}<div class="meta">${escapeHtml(meta)}</div></article>`;
}

function setButtonState(buttonEl, text, timeout = 1200) {
  if (!buttonEl) return;
  const original = buttonEl.dataset.originalText || buttonEl.textContent;
  buttonEl.dataset.originalText = original;
  buttonEl.textContent = text;
  window.setTimeout(() => {
    buttonEl.textContent = original;
  }, timeout);
}

function setControlStatus(text, isError = false) {
  if (!controlStatusEl) return;
  controlStatusEl.textContent = text;
  controlStatusEl.style.color = isError ? '#ff7b72' : '';
}

async function controlAction(buttonEl, url, options = {}) {
  const actionName = buttonEl?.dataset?.originalText || buttonEl?.textContent || 'Action';
  try {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    setButtonState(buttonEl, 'Done');
    setControlStatus(`${actionName} 완료`);
    await Promise.all([loadMessages(), loadStatus()]);
    return data;
  } catch (err) {
    setButtonState(buttonEl, 'Fail');
    setControlStatus(`${actionName} 실패`, true);
    throw err;
  }
}

async function copyDebugLog() {
  const text = (debugLogEl.textContent || '').trim();
  if (!text || text === '로그 없음' || text === '대기 중...') {
    setButtonState(copyDebugBtnEl, 'Empty');
    return;
  }

  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      await navigator.clipboard.writeText(text);
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    setButtonState(copyDebugBtnEl, 'Copied');
  } catch (err) {
    setButtonState(copyDebugBtnEl, 'Failed');
  }
}

async function clearDebugLog() {
  try {
    const res = await fetch('/api/debug/clear', { method: 'POST' });
    if (!res.ok) throw new Error('clear failed');
    lastLogSignature = '';
    debugLines = [];
    debugLogEl.textContent = '로그 없음';
    setButtonState(clearDebugBtnEl, 'Cleared');
    await loadStatus();
  } catch (err) {
    setButtonState(clearDebugBtnEl, 'Failed');
  }
}

function scrollDebugBy(direction) {
  const amount = Math.max(120, Math.floor(debugLogEl.clientHeight * 0.75));
  const delta = direction === 'up' ? -amount : amount;
  debugLogEl.scrollBy({ top: delta, behavior: 'smooth' });
}

async function loadMessages() {
  const res = await fetch('/api/messages');
  const data = await res.json();
  const messages = data.messages || [];
  const signature = JSON.stringify(messages.map((m) => [m.id, m.timestamp, m.text, m.file_path]));

  if (signature === lastSignature) return;

  lastSignature = signature;
  chatEl.innerHTML = messages.map(messageToHtml).join('');
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function loadStatus() {
  const res = await fetch('/api/status');
  const data = await res.json();

  const working = data.working || {};
  if (working.active) {
    statusEl.textContent = `running • message_id=${working.message_id || '-'}`;
  } else if (data.executor_running) {
    statusEl.textContent = `running • pid=${data.executor_pid || '-'}`;
  } else {
    statusEl.textContent = 'idle';
  }

  const pendingCount = Number(data.pending_count || 0);
  const pendingIds = Array.isArray(data.pending_ids) ? data.pending_ids.join(', ') : '';
  debugMetaEl.textContent = pendingIds ? `pending: ${pendingCount} [${pendingIds}]` : `pending: ${pendingCount}`;

  const logs = Array.isArray(data.log_tail) ? data.log_tail : [];
  const logSignature = JSON.stringify(logs);
  if (logSignature !== lastLogSignature) {
    const keepBottom = isNearBottom(debugLogEl);
    lastLogSignature = logSignature;
    if (logs.length === 0) {
      setDebugContent([], keepBottom);
      return;
    }

    if (debugLines.length === 0) {
      setDebugContent(logs, keepBottom);
      return;
    }

    const overlap = findOverlap(debugLines, logs);
    if (overlap === 0) {
      setDebugContent(logs, keepBottom);
      return;
    }

    const merged = debugLines.concat(logs.slice(overlap));
    setDebugContent(merged, keepBottom);
  }
}

formEl.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = '';

  await fetch('/api/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });

  await loadMessages();
  await loadStatus();
});

if (copyDebugBtnEl) {
  copyDebugBtnEl.addEventListener('click', copyDebugLog);
}

if (clearDebugBtnEl) {
  clearDebugBtnEl.addEventListener('click', clearDebugLog);
}

if (scrollDebugUpBtnEl) {
  scrollDebugUpBtnEl.addEventListener('click', () => scrollDebugBy('up'));
}

if (scrollDebugDownBtnEl) {
  scrollDebugDownBtnEl.addEventListener('click', () => scrollDebugBy('down'));
}

if (retriggerBtnEl) {
  retriggerBtnEl.addEventListener('click', async () => {
    await controlAction(retriggerBtnEl, '/api/control/retrigger', { method: 'POST' });
  });
}

if (testPingBtnEl) {
  testPingBtnEl.addEventListener('click', async () => {
    await controlAction(testPingBtnEl, '/api/control/test-message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: `웹 테스트 메시지 ${new Date().toLocaleTimeString()}` }),
    });
  });
}

if (stopWorkerBtnEl) {
  stopWorkerBtnEl.addEventListener('click', async () => {
    await controlAction(stopWorkerBtnEl, '/api/control/stop-worker', { method: 'POST' });
  });
}

async function tick() {
  try {
    await Promise.all([loadMessages(), loadStatus()]);
  } catch (err) {
    statusEl.textContent = 'error';
  }
}

tick();
setInterval(tick, 2000);
