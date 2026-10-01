/**
 * script.js — DocuMind AI frontend logic
 *
 * Handles:
 *  - Drag-and-drop + browse PDF selection
 *  - File info display (name + size)
 *  - POST /api/upload with loading state
 *  - Status bar update after upload
 *  - POST /api/ask with loading skeleton
 *  - Answer display with source page tags
 *  - All error states
 *  - Enter-key shortcut on question textarea
 */

'use strict';

/* --------------------------------------------------------------------------
   DOM references
   -------------------------------------------------------------------------- */
const uploadZone      = document.getElementById('upload-zone');
const pdfInput        = document.getElementById('pdf-input');
const browseBtn       = document.getElementById('browse-btn');
const fileInfo        = document.getElementById('file-info');
const fileInfoName    = document.getElementById('file-info-name');
const fileInfoSize    = document.getElementById('file-info-size');
const fileClearBtn    = document.getElementById('file-clear-btn');
const uploadBtn       = document.getElementById('upload-btn');
const uploadResult    = document.getElementById('upload-result');

const statusBar       = document.getElementById('status-bar');
const statusDot       = document.getElementById('status-dot');
const statusText      = document.getElementById('status-text');

const questionInput   = document.getElementById('question-input');
const askBtn          = document.getElementById('ask-btn');
const answerSection   = document.getElementById('answer-section');
const answerBox       = document.getElementById('answer-box');
const answerError     = document.getElementById('answer-error');
const sourcesLabel    = document.getElementById('sources-label');
const sourcesList     = document.getElementById('sources-list');

/* --------------------------------------------------------------------------
   State
   -------------------------------------------------------------------------- */
let selectedFile      = null;
let documentLoaded    = false;

/* --------------------------------------------------------------------------
   Utilities
   -------------------------------------------------------------------------- */

function formatBytes(bytes) {
  if (bytes < 1024)       return bytes + ' B';
  if (bytes < 1048576)    return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(2) + ' MB';
}

function setUploadBtnState(loading) {
  if (loading) {
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="spinner"></span> Processing…';
  } else {
    uploadBtn.disabled = !selectedFile;
    uploadBtn.innerHTML = '<span>📤</span> Upload & Process';
  }
}

function setAskBtnState(loading) {
  if (loading) {
    askBtn.disabled = true;
    askBtn.innerHTML = '<span class="spinner"></span> Thinking…';
  } else {
    askBtn.disabled = !documentLoaded;
    askBtn.innerHTML = '<span>💬</span> Ask';
  }
}

/* --------------------------------------------------------------------------
   File selection helpers
   -------------------------------------------------------------------------- */

function applyFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showUploadResult('error', '⚠ Only PDF files are accepted. Please select a .pdf file.');
    return;
  }
  selectedFile = file;
  fileInfoName.textContent = file.name;
  fileInfoSize.textContent = formatBytes(file.size);
  fileInfo.classList.add('visible');
  uploadBtn.disabled = false;
  // Clear any previous result when a new file is selected.
  uploadResult.className = 'upload-result';
  uploadResult.innerHTML = '';
}

function clearFile() {
  selectedFile = null;
  pdfInput.value = '';
  fileInfo.classList.remove('visible');
  fileInfoName.textContent = '';
  fileInfoSize.textContent = '';
  uploadBtn.disabled = true;
  uploadResult.className = 'upload-result';
  uploadResult.innerHTML = '';
}

/* --------------------------------------------------------------------------
   Drag-and-drop
   -------------------------------------------------------------------------- */

uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});

['dragleave', 'dragend'].forEach((evt) => {
  uploadZone.addEventListener(evt, () => uploadZone.classList.remove('drag-over'));
});

uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  applyFile(file);
});

// Clicking anywhere in the zone (except the browse button itself) also opens
// the file picker, so the whole zone is clickable.
uploadZone.addEventListener('click', (e) => {
  if (e.target === browseBtn || browseBtn.contains(e.target)) return;
  pdfInput.click();
});

browseBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  pdfInput.click();
});

pdfInput.addEventListener('change', () => {
  if (pdfInput.files.length > 0) applyFile(pdfInput.files[0]);
});

fileClearBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  clearFile();
});

/* --------------------------------------------------------------------------
   Status bar
   -------------------------------------------------------------------------- */

function setStatus(ready, text) {
  documentLoaded = ready;
  statusText.textContent = text;
  if (ready) {
    statusBar.classList.add('ready');
    questionInput.disabled = false;
    questionInput.placeholder = 'Type your question about the document…';
  } else {
    statusBar.classList.remove('ready');
    questionInput.disabled = true;
    questionInput.placeholder = 'Upload a PDF first to enable questions…';
  }
  setAskBtnState(false);
}

/* --------------------------------------------------------------------------
   Upload result banner
   -------------------------------------------------------------------------- */

/**
 * Escape a plain-text string so it is safe to insert via innerHTML.
 * Converts &, <, >, ", ' to their HTML entities.
 */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function showUploadResult(type, message, stats) {
  uploadResult.className = `upload-result visible ${type}`;
  // message is a plain-text string — escape before innerHTML to prevent
  // unintended HTML injection (e.g. from a filename containing < or &).
  let html = `<div>${escapeHtml(message)}</div>`;
  if (stats) {
    // stats.pages and stats.chunks are integers from the server — safe to
    // render directly, but escape defensively.
    html += `
      <div class="upload-stats">
        <div class="upload-stat">
          <span class="upload-stat-value">${escapeHtml(stats.pages)}</span>
          <span class="upload-stat-label">Pages</span>
        </div>
        <div class="upload-stat">
          <span class="upload-stat-value">${escapeHtml(stats.chunks)}</span>
          <span class="upload-stat-label">Chunks indexed</span>
        </div>
      </div>`;
  }
  uploadResult.innerHTML = html;
}

/* --------------------------------------------------------------------------
   Upload handler
   -------------------------------------------------------------------------- */

uploadBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  setUploadBtnState(true);
  uploadResult.className = 'upload-result';
  uploadResult.innerHTML = '';

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.success) {
      showUploadResult(
        'success',
        `✓ "${data.filename}" uploaded and indexed successfully.`,
        { pages: data.pages, chunks: data.chunks }
      );
      setStatus(true, `Active document: ${data.filename}  (${data.pages} pages, ${data.chunks} chunks)`);
      // Reset answer area when a new doc is loaded.
      answerSection.classList.remove('visible');
      answerBox.textContent = '';
      answerError.textContent = '';
      sourcesList.innerHTML = '';
      sourcesLabel.style.display = 'none';
    } else {
      showUploadResult('error', `✗ ${data.error}`);
    }
  } catch (err) {
    showUploadResult('error', '✗ Network error — could not reach the server. Is Flask running?');
    console.error('Upload error:', err);
  } finally {
    setUploadBtnState(false);
  }
});

/* --------------------------------------------------------------------------
   Answer display helpers
   -------------------------------------------------------------------------- */

function showSkeleton() {
  answerSection.classList.add('visible');
  answerError.textContent = '';
  answerError.style.display = 'none';
  sourcesLabel.style.display = 'none';
  sourcesList.innerHTML = '';
  answerBox.style.display = 'block';
  answerBox.innerHTML = `
    <div class="skeleton skeleton-line" style="width:92%"></div>
    <div class="skeleton skeleton-line" style="width:80%"></div>
    <div class="skeleton skeleton-line" style="width:87%"></div>
    <div class="skeleton skeleton-line"></div>`;
}

/**
 * Safely render a plain-text answer string that may contain minimal
 * Markdown syntax emitted by the LLM.
 *
 * Strategy (XSS-safe):
 *   1. Escape the raw text so any LLM-produced HTML characters are inert.
 *   2. Apply regex replacements ONLY for **bold** and *italic* patterns,
 *      inserting the controlled <strong>/<em> tags we know are safe.
 *   3. Set via innerHTML — the only HTML present is what we introduced in
 *      step 2, never raw LLM output.
 *
 * This renders "4.3% of GDP" instead of "**4.3% of GDP**".
 */
function renderMarkdown(text) {
  // Step 1: escape — neutralise all HTML special characters in the raw text.
  let escaped = escapeHtml(text);

  // Step 2: apply only **bold** and *italic* patterns on the escaped string.
  // **bold** — must come before *italic* to avoid partial matches.
  escaped = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // *italic* — single asterisks that are not part of a bold pair.
  escaped = escaped.replace(/\*([^*\n]+?)\*/g, '<em>$1</em>');

  // Preserve line breaks so multi-paragraph answers stay readable.
  escaped = escaped.replace(/\n/g, '<br>');

  return escaped;
}

function showAnswer(answer, sources) {
  answerBox.style.display = 'block';
  // Use the safe markdown renderer — NOT raw innerHTML of LLM output.
  answerBox.innerHTML = renderMarkdown(answer);

  answerError.style.display = 'none';

  if (sources && sources.length > 0) {
    sourcesLabel.style.display = 'block';
    sourcesList.innerHTML = sources
      .map(
        (s) =>
          `<span class="source-tag">📄 Page ${s.page}<span class="source-tag-score">· ${s.score}</span></span>`
      )
      .join('');
  } else {
    sourcesLabel.style.display = 'none';
    sourcesList.innerHTML = '';
  }
}

function showAnswerError(message) {
  answerBox.style.display = 'none';
  answerBox.innerHTML = '';
  answerError.textContent = message;
  answerError.style.display = 'block';
  sourcesLabel.style.display = 'none';
  sourcesList.innerHTML = '';
}

/* --------------------------------------------------------------------------
   Ask handler
   -------------------------------------------------------------------------- */

async function submitQuestion() {
  const question = questionInput.value.trim();
  if (!question || !documentLoaded) return;

  setAskBtnState(true);
  showSkeleton();

  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();

    if (data.success) {
      showAnswer(data.answer, data.sources);
    } else {
      showAnswerError(`✗ ${data.error}`);
    }
  } catch (err) {
    showAnswerError('✗ Network error — could not reach the server. Is Flask running?');
    console.error('Ask error:', err);
  } finally {
    setAskBtnState(false);
  }
}

askBtn.addEventListener('click', submitQuestion);

// Submit on Ctrl+Enter or Cmd+Enter.
questionInput.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    submitQuestion();
  }
});

/* --------------------------------------------------------------------------
   Auto-resize textarea
   -------------------------------------------------------------------------- */
questionInput.addEventListener('input', () => {
  questionInput.style.height = 'auto';
  questionInput.style.height = Math.min(questionInput.scrollHeight, 140) + 'px';
});

/* --------------------------------------------------------------------------
   Init — check server state on page load
   -------------------------------------------------------------------------- */
(async () => {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    if (data.document_loaded && data.current_document) {
      setStatus(true, `Active document: ${data.current_document}`);
    }
  } catch {
    // Server not reachable yet — leave default state.
  }
})();
