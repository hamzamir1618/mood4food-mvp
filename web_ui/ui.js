import { state } from './state.js';

// ── DOM Refs ───────────────────────────────────────────────────────────────
export const $main    = document.getElementById('main-content');
export const $loading = document.getElementById('loading-state');
export const $error   = document.getElementById('error-state');
export const $errorMsg = document.getElementById('error-message');
export const $chips   = document.getElementById('file-chips');

// ── State Transitions ──────────────────────────────────────────────────────
export function showLoading() {
  $loading.style.display = 'flex';
  $error.style.display = 'none';
  $main.style.display = 'none';
}

export function showError(msg) {
  $loading.style.display = 'none';
  $error.style.display = 'flex';
  $main.style.display = 'none';
  $errorMsg.textContent = msg || 'Something went wrong.';
}

export function showContent() {
  $loading.style.display = 'none';
  $error.style.display = 'none';
  $main.style.display = 'flex';
}

// ── File UI ────────────────────────────────────────────────────────────────
export function updateFileChips() {
  $chips.innerHTML = '';
  if (state.audioFile) {
    $chips.innerHTML += `<div class="file-chip">🎤 ${state.audioFile.name}<button type="button" class="chip-remove" onclick="removeFile('audio')" aria-label="Remove audio file ${escapeHtml(state.audioFile.name)}">✕</button></div>`;
  }
  if (state.imageFile) {
    $chips.innerHTML += `<div class="file-chip">📷 ${state.imageFile.name}<button type="button" class="chip-remove" onclick="removeFile('image')" aria-label="Remove image file ${escapeHtml(state.imageFile.name)}">✕</button></div>`;
  }
}

// ── Utility Label Helpers ──────────────────────────────────────────────────
export function healthLabel(v) { return v > 0.8 ? 'Excellent' : v > 0.5 ? 'Good' : 'Low'; }
export function budgetLabel(v) { return v > 0.7 ? 'Great Value' : v > 0.4 ? 'Fair' : 'Pricey'; }
export function tasteLabel(v) { return v > 0.8 ? 'Perfect Match' : v > 0.5 ? 'Good Match' : 'Mild Match'; }

// ── Full Render ────────────────────────────────────────────────────────────
export function render() {
  if (!state.blueprint) return;
  showContent();

  const dish = state.blueprint.winning_dish || {};
  const scores = state.blueprint.utility_breakdown || {};
  const wts = state.blueprint.agent_weights || {};
  const traces = state.blueprint.xai_traces || [];
  const candidates = state.blueprint.all_candidate_scores || [];
  const context = state.blueprint.source_context || {};
  const personas = state.blueprint.personas_available || {};
  const fulfillment = state.blueprint.fulfillment || {};

  const hasWinner = dish && dish.dish_id;

  $main.innerHTML = `
    ${renderContextBar(context)}
    ${renderPersonaBar(personas)}
    ${hasWinner ? `
      ${renderRelaxationNotice(state.blueprint.relaxation_notice)}
      ${renderWinnerCard(dish, scores)}
      <div id="runners-up-container">${renderRunnersUp(state.blueprint.top_candidates, dish.dish_id)}</div>
      ${renderCtaRow(fulfillment)}
      <div class="controls-row">
        <div class="controls-left">
          ${renderScoresCard(scores, traces, dish)}
        </div>
        <div class="controls-right">
          ${renderSliderGroup(wts)}
        </div>
      </div>
      ${renderRestaurants(fulfillment)}
      ${renderCandidates(candidates, dish.dish_id)}
    ` : `
      <div class="empty-state-container">
        <div class="empty-state-icon">🍽️</div>
        <h3>No exact matches found</h3>
        <p>We couldn't find a dish that strictly meets your requirements.<br>Try loosening your budget or switching up the persona sliders below!</p>
      </div>
      <div class="controls-row" style="justify-content: center; max-width: 600px; margin: 40px auto 20px;">
        <div class="controls-right" style="width: 100%;">
          ${renderSliderGroup(wts)}
        </div>
      </div>
    `}
    ${renderXaiSection(traces)}
    <footer class="app-footer">
      Powered by <a href="#">FIPE Engine</a> — Graph Theory × Game Theory × Compiler Design
    </footer>
  `;
}

// ── Fast Update (sliders/persona) ──────────────────────────────────────────
export function updateDynamic() {
  if (!state.blueprint) return;
  const dish = state.blueprint.winning_dish || {};
  const scores = state.blueprint.utility_breakdown || {};
  const traces = state.blueprint.xai_traces || [];
  const candidates = state.blueprint.all_candidate_scores || [];
  const fulfillment = state.blueprint.fulfillment || {};

  // Winner card
  const $wCard = document.getElementById('winner-card');
  if ($wCard) {
    const imgUrl = dish.image_url || '';
    $wCard.style.backgroundImage = imgUrl ? `linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.15) 50%, transparent 100%), url('${imgUrl}')` : '';
  }
  const $wName = document.getElementById('winner-name');
  const $wPrice = document.getElementById('winner-price');
  const $wScore = document.getElementById('winner-score');
  const $wCat = document.getElementById('winner-category');
  const $wTags = document.getElementById('winner-tags');
  if ($wName) $wName.textContent = dish.name || 'No dish';
  if ($wPrice) $wPrice.textContent = `Rs. ${dish.price_pkr ?? '—'}`;
  if ($wScore) {
    const pct = ((scores.u_total ?? 0) * 100).toFixed(0);
    $wScore.textContent = `⚡ ${pct}% Match`;
  }
  if ($wCat) $wCat.textContent = dish.category || '';
  if ($wTags) $wTags.innerHTML = (dish.human_tags || []).map(t => `<span class="tag-pill">${t}</span>`).join('');

  // Pulse winner card
  if ($wCard) { $wCard.classList.remove('pulse'); void $wCard.offsetWidth; $wCard.classList.add('pulse'); }

  const $altBtn = document.getElementById('btn-alternate');
  if ($altBtn) {
    $altBtn.disabled = false;
    $altBtn.textContent = 'Not quite — show me something else';
  }

  // Runners up
  const $runnersUp = document.getElementById('runners-up-container');
  if ($runnersUp) {
    $runnersUp.innerHTML = renderRunnersUp(state.blueprint.top_candidates, dish.dish_id);
  }

  // Score bars
  const reasons = parseReasons(traces, dish?.name);
  updateScoreBar('health', scores.u_health, healthLabel, reasons.health);
  updateScoreBar('budget', scores.u_budget, budgetLabel, reasons.budget);
  updateScoreBar('taste', scores.u_taste, tasteLabel, reasons.taste);

  // Candidates
  const $grid = document.getElementById('candidates-grid');
  const $count = document.getElementById('candidates-count');
  if ($grid) $grid.innerHTML = renderCandidateCards(candidates, dish.dish_id);
  if ($count) $count.textContent = `${candidates.length} dishes`;

  // XAI
  const $xaiInner = document.getElementById('xai-inner');
  if ($xaiInner) $xaiInner.innerHTML = renderXaiLines(traces);

  // CTA / restaurants
  const $restaurants = document.getElementById('restaurants-container');
  if ($restaurants && fulfillment.restaurants) {
    $restaurants.innerHTML = fulfillment.restaurants.map(r => renderRestaurantCard(r)).join('');
  }
}

export function updateScoreBar(cls, value, labelFn, reasonText) {
  const val = value ?? 0;
  const pct = (val * 100).toFixed(0);
  const $fill = document.querySelector(`.score-bar-fill.${cls}`);
  const $val = document.querySelector(`.score-value.${cls}`);
  const $label = document.querySelector(`.score-label-text.${cls}`);
  const $reason = document.querySelector(`.score-reason.${cls}`);
  if ($fill) $fill.style.width = `${Math.min(val * 100, 100)}%`;
  if ($val) $val.textContent = `${pct}%`;
  if ($label) $label.textContent = labelFn(val);
  if ($reason && reasonText !== undefined) {
    $reason.textContent = `↳ ${reasonText}`;
  }
}

// ── Recipe Modal ───────────────────────────────────────────────────────────
export function renderRecipeModalContent(recipe) {
  const dish = state.blueprint?.winning_dish || {};
  const totalCost = (recipe.grocery_list || []).reduce((s, g) => s + (g.est_cost || 0), 0);

  return `
    <div class="recipe-header">
      <div class="recipe-header-top">
        <h2>🍳 ${dish.name || 'Recipe'}</h2>
        <button class="recipe-close" id="recipe-close-btn" aria-label="Close recipe">✕</button>
      </div>
      <div class="recipe-meta-row">
        <span class="recipe-meta-pill">⏱ Prep: ${recipe.prep_time || '—'}</span>
        <span class="recipe-meta-pill">🔥 Cook: ${recipe.cook_time || '—'}</span>
        <span class="recipe-meta-pill">🍽 Serves: ${recipe.servings || '—'}</span>
        <span class="recipe-meta-pill difficulty-${(recipe.difficulty || '').toLowerCase()}">${recipe.difficulty || '—'}</span>
      </div>
    </div>
    <div class="recipe-body">
      <h3>📋 Steps</h3>
      <ol class="recipe-steps">
        ${(recipe.steps || []).map(s => `<li>${escapeHtml(s)}</li>`).join('')}
      </ol>
      <h3>🛒 Grocery List <span class="grocery-total">Est. Total: Rs. ${totalCost}</span></h3>
      <div class="grocery-grid">
        ${(recipe.grocery_list || []).map(g => `
          <div class="grocery-item">
            <span class="grocery-name">${escapeHtml(g.item)}</span>
            <span class="grocery-qty">${g.qty}</span>
            <span class="grocery-cost">Rs. ${g.est_cost}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

// ── Components ─────────────────────────────────────────────────────────────
function renderRelaxationNotice(notice) {
  if (!notice) return '';
  return `
    <div class="relaxation-notice">
      <div class="relaxation-icon">⚠️</div>
      <div class="relaxation-text">${escapeHtml(notice)}</div>
    </div>
  `;
}

function renderContextBar(ctx) {
  const budget = ctx.budget_max_pkr || '—';
  const allergens = (ctx.allergens_pruned || []).join(', ') || 'None';
  const mood = ctx.mood_vector_seed || 'neutral';
  return `
    <div class="context-bar">
      <div class="context-chip"><span class="chip-icon">💰</span> Budget: <span class="chip-value">Rs. ${budget}</span></div>
      <div class="context-chip"><span class="chip-icon">🚫</span> Excluded: <span class="chip-value">${capitalize(allergens)}</span></div>
      <div class="context-chip"><span class="chip-icon">🎯</span> Mood: <span class="chip-value">${capitalize(mood)}</span></div>
    </div>
  `;
}

function renderPersonaBar(personas) {
  if (!personas || !Object.keys(personas).length) return '';
  const chips = Object.entries(personas).map(([key, p]) => {
    const active = key === state.currentPersona ? 'active' : '';
    return `<button class="persona-chip ${active}" data-persona="${key}" aria-label="Persona: ${p.display_name}" aria-pressed="${key === state.currentPersona}">
      <span class="persona-icon">${p.icon}</span>
      <span class="persona-name">${p.display_name}</span>
    </button>`;
  }).join('');
  return `<div class="persona-bar"><div class="persona-scroll">${chips}</div></div>`;
}

function renderWinnerCard(dish, scores) {
  const name = dish.name || 'No dish selected';
  const price = dish.price_pkr ?? '—';
  const pct = ((scores.u_total ?? 0) * 100).toFixed(0);
  const imgUrl = dish.image_url || '';
  const bgStyle = imgUrl
    ? `background-image: linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.15) 50%, transparent 100%), url('${imgUrl}');`
    : '';
  const tags = (dish.human_tags || []).map(t => `<span class="tag-pill">${t}</span>`).join('');

  return `
    <div class="winner-card" id="winner-card" style="${bgStyle}">
      <div class="winner-card-content">
        <div class="winner-label">🏆 Best Pick For You</div>
        <div class="winner-dish-name" id="winner-name">${name}</div>
        <div class="winner-tags" id="winner-tags">${tags}</div>
        <div class="winner-meta">
          <span class="winner-meta-item" id="winner-price">🏷️ Rs. ${price}</span>
          <span class="winner-meta-item winner-category" id="winner-category">${dish.category || ''}</span>
        </div>
        <div class="winner-score-badge" id="winner-score">⚡ ${pct}% Match</div>
        <button id="btn-alternate" class="btn-alternate">Not quite — show me something else</button>
      </div>
    </div>
  `;
}

function renderRunnersUp(candidates, winnerId) {
  if (!candidates || !candidates.length) return '';
  const runners = candidates.filter(c => c.dish_id !== winnerId).slice(0, 4);
  if (!runners.length) return '';

  const cards = runners.map(c => {
    const imgStyle = c.image_url ? `background-image: url('${c.image_url}');` : '';
    const totalScore = ((c.u_total ?? 0) * 100).toFixed(0);
    const health = ((c.u_health ?? 0) * 100).toFixed(0);
    const budget = ((c.u_budget ?? 0) * 100).toFixed(0);
    const taste = ((c.u_taste ?? 0) * 100).toFixed(0);

    return `
      <div class="runner-card">
        <div class="runner-card-header">
          <div class="runner-img" style="${imgStyle}"></div>
          <div class="runner-info">
            <div class="runner-name">${escapeHtml(c.name)}</div>
            <div class="runner-score">⚡ ${totalScore}% Match</div>
          </div>
          <button class="runner-expand-btn" aria-label="Expand breakdown">▼</button>
        </div>
        <div class="runner-breakdown">
          <div class="runner-bd-row"><span class="bd-label">💪 Health</span><div class="bd-bar-bg"><div class="bd-bar-fill health" style="width: ${health}%"></div></div></div>
          <div class="runner-bd-row"><span class="bd-label">💰 Budget</span><div class="bd-bar-bg"><div class="bd-bar-fill budget" style="width: ${budget}%"></div></div></div>
          <div class="runner-bd-row"><span class="bd-label">😋 Taste</span><div class="bd-bar-bg"><div class="bd-bar-fill taste" style="width: ${taste}%"></div></div></div>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div class="runners-up-section">
      <h3 class="runners-up-title">Other Top Matches</h3>
      <div class="runners-up-row">${cards}</div>
    </div>
  `;
}

function renderCtaRow(fulfillment) {
  return `
    <div class="cta-row">
      <button class="cta-btn cta-recipe" id="cta-recipe">🍳 View Recipe</button>
      <button class="cta-btn cta-order" id="cta-order">🛵 Order Nearby</button>
    </div>
  `;
}

function parseReasons(traces, winnerName) {
  let reasons = { health: '', budget: '', taste: '' };
  if (!traces || !winnerName) return reasons;
  const idx = traces.findIndex(t => t.includes(winnerName) && t.includes('Candidate Breakdown'));
  if (idx !== -1) {
    const lines = traces.slice(idx + 1, idx + 4);
    lines.forEach(l => {
      const match = l.match(/- (\w+) Agent: (.*?)(?: \(raw:|$)/);
      if (match) {
        if (match[1] === 'Health') reasons.health = match[2].trim();
        if (match[1] === 'Budget') reasons.budget = match[2].trim();
        if (match[1] === 'Taste') reasons.taste = match[2].trim();
      }
    });
  }
  return reasons;
}

function renderScoresCard(scores, traces, dish) {
  const reasons = parseReasons(traces, dish?.name);
  const items = [
    { label: 'Healthy', key: 'u_health', cls: 'health', labelFn: healthLabel, reason: reasons.health },
    { label: 'Affordable', key: 'u_budget', cls: 'budget', labelFn: budgetLabel, reason: reasons.budget },
    { label: 'Tasty', key: 'u_taste', cls: 'taste', labelFn: tasteLabel, reason: reasons.taste },
  ];
  const rows = items.map(item => {
    const val = scores[item.key] ?? 0;
    const pct = (val * 100).toFixed(0);
    const lab = item.labelFn(val);
    return `
      <div class="score-row-wrapper">
        <div class="score-row">
          <div class="score-label">
            <div class="score-dot ${item.cls}"></div>
            <span class="score-label-text ${item.cls}">${lab}</span>
          </div>
          <div class="score-bar-container">
            <div class="score-bar-fill ${item.cls}" style="width: ${Math.min(val * 100, 100)}%"></div>
          </div>
          <div class="score-value ${item.cls}">${pct}%</div>
        </div>
        ${item.reason ? `<div class="score-reason ${item.cls}">↳ ${escapeHtml(item.reason)}</div>` : ''}
      </div>
    `;
  }).join('');
  return `<div class="scores-card"><h2><span>📊</span> How It Scores</h2>${rows}</div>`;
}

function renderSliderGroup(wts) {
  const sliders = [
    { id: 'slider-health', label: '💪 Health', key: 'w_h', cls: 'health' },
    { id: 'slider-budget', label: '💰 Budget', key: 'w_b', cls: 'budget' },
    { id: 'slider-taste',  label: '😋 Taste',  key: 'w_t', cls: 'taste' },
  ];
  const rows = sliders.map(s => {
    const val = state.weights[s.key] ?? 0.33;
    return `
      <div class="slider-row">
        <span class="slider-label">${s.label}</span>
        <input type="range" class="priority-slider ${s.cls}" id="${s.id}"
               min="0" max="1" step="0.01" value="${val}" aria-label="${s.label} Priority">
        <span class="slider-val" id="${s.id}-val">${(val * 100).toFixed(0)}%</span>
      </div>
    `;
  }).join('');
  return `<div class="slider-group"><h2><span>⚖️</span> Your Priorities</h2>${rows}</div>`;
}

function renderRestaurants(fulfillment) {
  const restaurants = fulfillment.restaurants || [];
  if (!restaurants.length) return '';
  return `
    <div class="restaurants-section" id="restaurants-section" style="display:none;">
      <h2><span>🛵</span> Order Nearby</h2>
      <div class="restaurants-grid" id="restaurants-container">
        ${restaurants.map(r => renderRestaurantCard(r)).join('')}
      </div>
    </div>
  `;
}

function renderRestaurantCard(r) {
  const stars = '⭐'.repeat(Math.round(r.rating || 0));
  return `
    <div class="restaurant-card">
      <div class="restaurant-name">${escapeHtml(r.name)}</div>
      <div class="restaurant-meta">
        <span>🕐 ${r.delivery_time || '—'}</span>
        <span>💰 +Rs. ${r.delivery_fee || 0}</span>
      </div>
      <div class="restaurant-rating">${stars} ${(r.rating || 0).toFixed(1)}</div>
      <button class="restaurant-order-btn">Place Order</button>
    </div>
  `;
}

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
    const pct = ((c.u_total ?? 0) * 100).toFixed(0);
    const imgUrl = c.image_url || '';
    const tags = (c.human_tags || []).slice(0, 2).map(t => `<span class="tag-pill-dark">${t}</span>`).join('');
    const imgStyle = imgUrl ? `background-image: url('${imgUrl}');` : '';
    return `
      <div class="candidate-card ${isWinner ? 'is-winner' : ''}">
        <div class="candidate-img" style="${imgStyle}"></div>
        <div class="candidate-body">
          <div class="candidate-rank">#${i + 1}</div>
          <div class="candidate-name">${c.name || 'Unknown'}</div>
          <div class="candidate-category">${c.category || ''}</div>
          <div class="candidate-tags">${tags}</div>
          <div class="candidate-footer">
            <span class="candidate-price">Rs. ${c.price_pkr ?? '—'}</span>
            <span class="candidate-total">${pct}%</span>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderXaiSection(traces) {
  if (!traces.length) return '';
  return `
    <div class="xai-section">
      <button class="xai-toggle" id="xai-toggle">
        <span class="xai-toggle-left"><span>⚙️</span> Developer Mode — AI Reasoning Trace</span>
        <span class="xai-chevron ${state.xaiOpen ? 'open' : ''}" id="xai-chevron">▼</span>
      </button>
      <div class="xai-panel ${state.xaiOpen ? 'open' : ''}" id="xai-panel">
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

export function capitalize(str) { return str.charAt(0).toUpperCase() + str.slice(1); }
export function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}

// ── Toasts & Loading ───────────────────────────────────────────────────────
export function showToast(message, type = 'error') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icon = type === 'error' ? '⚠️' : '✅';
  toast.innerHTML = `<span class="toast-icon">${icon}</span> <span>${escapeHtml(message)}</span>`;
  
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'fadeOut 0.3s ease-out forwards';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

export function setUIEnabled(enabled) {
  const controlsRow = document.querySelector('.controls-row');
  const personaBar = document.querySelector('.persona-bar');
  if (controlsRow) controlsRow.classList.toggle('ui-disabled', !enabled);
  if (personaBar) personaBar.classList.toggle('ui-disabled', !enabled);
}

export function setRecalcLoading(loading) {
  const loader = document.getElementById('recalc-loading');
  if (loader) loader.style.display = loading ? 'flex' : 'none';
}
