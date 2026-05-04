/* ═══════════════════════════════════════════════════════════════════════════
   FIPE Mood4Food — Client-Side Logic
   Connects to FastAPI backend at /decision_blueprint and /recalculate
   ═══════════════════════════════════════════════════════════════════════════ */

const API_BASE = '';  // same origin — served by FastAPI

// ── State ──────────────────────────────────────────────────────────────────
let blueprint = null;
let budgetPriority = 0.3;
let debounceTimer = null;
let xaiOpen = false;
let firstRenderDone = false;

// ── DOM Refs ───────────────────────────────────────────────────────────────
const $main      = document.getElementById('main-content');
const $loading   = document.getElementById('loading-state');
const $error     = document.getElementById('error-state');
const $errorMsg  = document.getElementById('error-message');

// ── Boot ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('refresh-btn').addEventListener('click', fetchBlueprint);

  // Query form
  const form = document.getElementById('query-form');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const input = document.getElementById('query-input');
    const text = input.value.trim();
    if (text) submitQuery(text);
  });

  fetchBlueprint();
});

// ── Fetch Decision Blueprint ───────────────────────────────────────────────
async function fetchBlueprint() {
  showLoading();
  firstRenderDone = false;
  try {
    const resp = await fetch(`${API_BASE}/decision_blueprint`);
    if (!resp.ok) throw new Error(`Server responded ${resp.status}`);
    blueprint = await resp.json();
    budgetPriority = blueprint.agent_weights?.w_b ?? 0.3;
    render();
  } catch (err) {
    showError(err.message);
  }
}

// ── Submit New Query (full pipeline) ───────────────────────────────────────
async function submitQuery(queryText) {
  const $status = document.getElementById('query-status');
  const $submit = document.getElementById('query-submit');
  const $input  = document.getElementById('query-input');

  // Disable input while pipeline runs
  $submit.disabled = true;
  $input.disabled = true;
  $status.className = 'query-status running';
  $status.textContent = '⟳ Running pipeline… parsing intent → querying database → finding best dish…';

  showLoading();

  try {
    const resp = await fetch(`${API_BASE}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: queryText }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: `Server responded ${resp.status}` }));
      throw new Error(err.detail || `Server responded ${resp.status}`);
    }

    blueprint = await resp.json();
    budgetPriority = blueprint.agent_weights?.w_b ?? 0.3;
    firstRenderDone = false;
    render();

    $status.className = 'query-status success';
    $status.textContent = `✓ Found ${blueprint.all_candidate_scores?.length ?? 0} options — recommending ${blueprint.winning_dish?.name || 'a dish'}`;
    setTimeout(() => { $status.textContent = ''; $status.className = 'query-status'; }, 4000);
  } catch (err) {
    showError(err.message);
    $status.className = 'query-status error';
    $status.textContent = `✗ ${err.message}`;
  } finally {
    $submit.disabled = false;
    $input.disabled = false;
  }
}
async function recalculate(wBudget) {
  const $status = document.getElementById('slider-status');
  if ($status) { $status.classList.add('visible'); $status.textContent = '⟳ Updating…'; }

  try {
    const resp = await fetch(`${API_BASE}/recalculate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ w_budget: parseFloat(wBudget.toFixed(2)) }),
    });
    if (!resp.ok) throw new Error(`Server responded ${resp.status}`);
    blueprint = await resp.json();
    updateDynamic();
    if ($status) { $status.textContent = '✓ Done'; setTimeout(() => $status.classList.remove('visible'), 800); }
  } catch (err) {
    if ($status) { $status.textContent = '✗ Failed'; setTimeout(() => $status.classList.remove('visible'), 1500); }
  }
}

// ── State Transitions ──────────────────────────────────────────────────────
function showLoading() {
  $loading.style.display = 'flex';
  $error.style.display = 'none';
  $main.style.display = 'none';
}

function showError(msg) {
  $loading.style.display = 'none';
  $error.style.display = 'flex';
  $main.style.display = 'none';
  $errorMsg.textContent = msg || 'Something went wrong.';
}

function showContent() {
  $loading.style.display = 'none';
  $error.style.display = 'none';
  $main.style.display = 'flex';
}

// ── Full Render (first load / refresh only) ────────────────────────────────
function render() {
  if (!blueprint) return;
  showContent();

  const dish    = blueprint.winning_dish || {};
  const scores  = blueprint.utility_breakdown || {};
  const weights = blueprint.agent_weights || {};
  const traces  = blueprint.xai_traces || [];
  const candidates = blueprint.all_candidate_scores || [];
  const context = blueprint.source_context || {};

  budgetPriority = weights.w_b ?? budgetPriority;

  $main.innerHTML = `
    ${renderContextBar(context)}
    <div class="top-row">
      <div class="top-row-left">
        ${renderWinnerCard(dish, scores)}
      </div>
      <div class="top-row-right">
        ${renderScoresCard(scores)}
        ${renderSliderCard(weights)}
      </div>
    </div>
    ${renderCandidates(candidates, dish.dish_id)}
    ${renderXaiSection(traces)}
    <footer class="app-footer">
      Powered by <a href="#">FIPE Engine</a> — Graph Theory × Game Theory × Compiler Design
    </footer>
  `;

  bindSlider();
  bindXaiToggle();

  // After first paint, mark so future updates skip animations
  requestAnimationFrame(() => { firstRenderDone = true; $main.classList.add('rendered'); });
}

// ── Fast Targeted Update (slider changes only) ────────────────────────────
function updateDynamic() {
  if (!blueprint) return;
  const dish    = blueprint.winning_dish || {};
  const scores  = blueprint.utility_breakdown || {};
  const weights = blueprint.agent_weights || {};
  const traces  = blueprint.xai_traces || [];
  const candidates = blueprint.all_candidate_scores || [];

  // Update winner card
  const $wName = document.getElementById('winner-name');
  const $wPrice = document.getElementById('winner-price');
  const $wId = document.getElementById('winner-id');
  const $wScore = document.getElementById('winner-score');
  if ($wName) $wName.textContent = dish.name || 'No dish';
  if ($wPrice) $wPrice.textContent = `Rs. ${dish.price_pkr ?? '—'}`;
  if ($wId) $wId.textContent = dish.dish_id || '—';
  if ($wScore) {
    const pct = ((scores.u_total ?? 0) * 100).toFixed(1);
    $wScore.textContent = `⚡ Score: ${pct}%`;
  }
  // Pulse the winner card
  const $wCard = document.getElementById('winner-card');
  if ($wCard) { $wCard.classList.remove('pulse'); void $wCard.offsetWidth; $wCard.classList.add('pulse'); }

  // Update score bars
  updateScoreBar('health', scores.u_health);
  updateScoreBar('budget', scores.u_budget);
  updateScoreBar('taste', scores.u_taste);

  // Update candidates
  const $grid = document.getElementById('candidates-grid');
  const $count = document.getElementById('candidates-count');
  if ($grid) $grid.innerHTML = renderCandidateCards(candidates, dish.dish_id);
  if ($count) $count.textContent = `${candidates.length} dishes`;

  // Update XAI traces
  const $xaiInner = document.getElementById('xai-inner');
  if ($xaiInner) $xaiInner.innerHTML = renderXaiLines(traces);
}

function updateScoreBar(cls, value) {
  const val = value ?? 0;
  const pct = (val * 100).toFixed(1);
  const $fill = document.querySelector(`.score-bar-fill.${cls}`);
  const $val = document.querySelector(`.score-value.${cls}`);
  if ($fill) $fill.style.width = `${Math.min(val * 100, 100)}%`;
  if ($val) $val.textContent = `${pct}%`;
}

// ── Bind Events ────────────────────────────────────────────────────────────
function bindSlider() {
  const slider = document.getElementById('budget-slider');
  if (!slider) return;
  slider.addEventListener('input', (e) => {
    budgetPriority = parseFloat(e.target.value);
    const badge = document.getElementById('slider-badge');
    if (badge) badge.textContent = (budgetPriority * 100).toFixed(0) + '%';
  });
  slider.addEventListener('change', (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => recalculate(parseFloat(e.target.value)), 100);
  });
}

function bindXaiToggle() {
  const xaiToggle = document.getElementById('xai-toggle');
  if (!xaiToggle) return;
  xaiToggle.addEventListener('click', () => {
    xaiOpen = !xaiOpen;
    const panel = document.getElementById('xai-panel');
    const chevron = document.getElementById('xai-chevron');
    if (panel) panel.classList.toggle('open', xaiOpen);
    if (chevron) chevron.classList.toggle('open', xaiOpen);
  });
}

// ── Context Bar ────────────────────────────────────────────────────────────
function renderContextBar(ctx) {
  const budget = ctx.budget_max_pkr || '—';
  const allergens = (ctx.allergens_pruned || []).join(', ') || 'None';
  const mood = ctx.mood_vector_seed || 'neutral';

  return `
    <div class="context-bar">
      <div class="context-chip">
        <span class="chip-icon">💰</span>
        Budget: <span class="chip-value">Rs. ${budget}</span>
      </div>
      <div class="context-chip">
        <span class="chip-icon">🚫</span>
        Excluded: <span class="chip-value">${capitalize(allergens)}</span>
      </div>
      <div class="context-chip">
        <span class="chip-icon">🎯</span>
        Mood: <span class="chip-value">${capitalize(mood)}</span>
      </div>
    </div>
  `;
}

// ── Winner Card ────────────────────────────────────────────────────────────
function renderWinnerCard(dish, scores) {
  const name = dish.name || 'No dish selected';
  const price = dish.price_pkr ?? '—';
  const pct = ((scores.u_total ?? 0) * 100).toFixed(1);

  return `
    <div class="winner-card" id="winner-card">
      <div class="winner-label">🏆 Best Pick For You</div>
      <div class="winner-dish-name" id="winner-name">${name}</div>
      <div class="winner-meta">
        <div class="winner-meta-item" id="winner-price">
          <span class="meta-icon">🏷️</span>
          Rs. ${price}
        </div>
        <div class="winner-meta-item">
          <span class="meta-icon">🆔</span>
          <span id="winner-id">${dish.dish_id || '—'}</span>
        </div>
      </div>
      <div class="winner-score-badge" id="winner-score">⚡ Score: ${pct}%</div>
    </div>
  `;
}

// ── Score Breakdown ────────────────────────────────────────────────────────
function renderScoresCard(scores) {
  const items = [
    { label: 'Healthy',    key: 'u_health', cls: 'health' },
    { label: 'Affordable', key: 'u_budget', cls: 'budget' },
    { label: 'Tasty',      key: 'u_taste',  cls: 'taste' },
  ];

  const rows = items.map(item => {
    const val = (scores[item.key] ?? 0);
    const pct = (val * 100).toFixed(1);
    return `
      <div class="score-row">
        <div class="score-label">
          <div class="score-dot ${item.cls}"></div>
          <span class="score-label-text">${item.label}</span>
        </div>
        <div class="score-bar-container">
          <div class="score-bar-fill ${item.cls}" style="width: ${Math.min(val * 100, 100)}%"></div>
        </div>
        <div class="score-value ${item.cls}">${pct}%</div>
      </div>
    `;
  }).join('');

  return `
    <div class="scores-card">
      <h2><span>📊</span> Breakdown</h2>
      ${rows}
    </div>
  `;
}

// ── Slider Card ────────────────────────────────────────────────────────────
function renderSliderCard(weights) {
  const wB = weights.w_b ?? 0.3;
  return `
    <div class="slider-card">
      <div class="slider-header">
        <h2><span>⚖️</span> Budget Priority</h2>
        <div class="slider-badge" id="slider-badge">${(wB * 100).toFixed(0)}%</div>
      </div>
      <input type="range" class="budget-slider" id="budget-slider"
             min="0" max="1" step="0.1" value="${wB}">
      <div class="slider-labels">
        <span>Relaxed</span>
        <span>Strict</span>
      </div>
      <div class="slider-updating" id="slider-status"></div>
    </div>
  `;
}

// ── Candidates ─────────────────────────────────────────────────────────────
function renderCandidates(candidates, winnerId) {
  if (!candidates.length) return '';
  return `
    <div class="candidates-section">
      <div class="candidates-header">
        <h2><span>🍽️</span> All Options</h2>
        <span class="candidates-count" id="candidates-count">${candidates.length} dishes</span>
      </div>
      <div class="candidates-grid" id="candidates-grid">
        ${renderCandidateCards(candidates, winnerId)}
      </div>
    </div>
  `;
}

function renderCandidateCards(candidates, winnerId) {
  const sorted = [...candidates].sort((a, b) => (b.u_total ?? 0) - (a.u_total ?? 0));
  return sorted.map((c, i) => {
    const isWinner = c.dish_id === winnerId;
    const pct = ((c.u_total ?? 0) * 100).toFixed(1);
    const hPct = ((c.u_health ?? 0) * 100).toFixed(0);
    const bPct = ((c.u_budget ?? 0) * 100).toFixed(0);
    const tPct = ((c.u_taste ?? 0) * 100).toFixed(0);
    return `
      <div class="candidate-card ${isWinner ? 'is-winner' : ''}">
        <div class="candidate-rank">#${i + 1}</div>
        <div class="candidate-name">${c.name || 'Unknown'}</div>
        <div class="candidate-scores">
          <span class="candidate-score-pill health">💪${hPct}%</span>
          <span class="candidate-score-pill budget">💰${bPct}%</span>
          <span class="candidate-score-pill taste">😋${tPct}%</span>
        </div>
        <div class="candidate-footer">
          <span class="candidate-price">Rs. ${c.price_pkr ?? '—'}</span>
          <span class="candidate-total">${pct}%</span>
        </div>
      </div>
    `;
  }).join('');
}

// ── XAI Trace ──────────────────────────────────────────────────────────────
function renderXaiSection(traces) {
  if (!traces.length) return '';
  return `
    <div class="xai-section">
      <button class="xai-toggle" id="xai-toggle">
        <span class="xai-toggle-left">
          <span>🧠</span> How It Works — AI Reasoning Trace
        </span>
        <span class="xai-chevron ${xaiOpen ? 'open' : ''}" id="xai-chevron">▼</span>
      </button>
      <div class="xai-panel ${xaiOpen ? 'open' : ''}" id="xai-panel">
        <div class="xai-panel-inner" id="xai-inner">
          ${renderXaiLines(traces)}
        </div>
      </div>
    </div>
  `;
}

function renderXaiLines(traces) {
  return traces.map(t => {
    const isWinner = t.startsWith('winner:');
    return `<div class="xai-trace-line ${isWinner ? 'winner-line' : ''}">${escapeHtml(t)}</div>`;
  }).join('');
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}
