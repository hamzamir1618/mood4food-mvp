/* ═══════════════════════════════════════════════════════════════════════════
   FIPE Mood4Food — Client-Side Logic v2
   Personas, multi-axis sliders, recipes, restaurants, image-heavy UI
   ═══════════════════════════════════════════════════════════════════════════ */

const API_BASE = '';

// ── State ──────────────────────────────────────────────────────────────────
let blueprint = null;
let currentPersona = 'balanced';
let weights = { w_h: 0.34, w_b: 0.33, w_t: 0.33 };
let debounceTimer = null;
let xaiOpen = false;
let recipeOpen = false;
let firstRenderDone = false;

// ── DOM Refs ───────────────────────────────────────────────────────────────
const $main    = document.getElementById('main-content');
const $loading = document.getElementById('loading-state');
const $error   = document.getElementById('error-state');
const $errorMsg = document.getElementById('error-message');

// ── File State ─────────────────────────────────────────────────────────────
let audioFile = null;
let imageFile = null;

// ── Boot ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('refresh-btn').addEventListener('click', fetchBlueprint);

  const form = document.getElementById('query-form');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = document.getElementById('query-input').value.trim();
    if (text || audioFile || imageFile) submitQuery(text);
  });

  document.getElementById('audio-btn').addEventListener('click', () => {
    document.getElementById('audio-file').click();
  });
  document.getElementById('image-btn').addEventListener('click', () => {
    document.getElementById('image-file').click();
  });

  document.getElementById('audio-file').addEventListener('change', (e) => {
    audioFile = e.target.files[0] || null;
    document.getElementById('audio-btn').classList.toggle('has-file', !!audioFile);
    updateFileChips();
  });
  document.getElementById('image-file').addEventListener('change', (e) => {
    imageFile = e.target.files[0] || null;
    document.getElementById('image-btn').classList.toggle('has-file', !!imageFile);
    updateFileChips();
  });

  // Recipe modal backdrop close
  document.getElementById('recipe-modal-backdrop').addEventListener('click', closeRecipeModal);

  fetchBlueprint();
});

function updateFileChips() {
  const $chips = document.getElementById('file-chips');
  $chips.innerHTML = '';
  if (audioFile) {
    $chips.innerHTML += `<div class="file-chip">🎤 ${audioFile.name}<button class="chip-remove" onclick="removeFile('audio')">✕</button></div>`;
  }
  if (imageFile) {
    $chips.innerHTML += `<div class="file-chip">📷 ${imageFile.name}<button class="chip-remove" onclick="removeFile('image')">✕</button></div>`;
  }
}

function removeFile(type) {
  if (type === 'audio') {
    audioFile = null;
    document.getElementById('audio-file').value = '';
    document.getElementById('audio-btn').classList.remove('has-file');
  } else {
    imageFile = null;
    document.getElementById('image-file').value = '';
    document.getElementById('image-btn').classList.remove('has-file');
  }
  updateFileChips();
}

// ── Fetch Blueprint ────────────────────────────────────────────────────────
async function fetchBlueprint() {
  showLoading();
  firstRenderDone = false;
  try {
    const resp = await fetch(`${API_BASE}/decision_blueprint`);
    if (!resp.ok) throw new Error(`Server responded ${resp.status}`);
    blueprint = await resp.json();
    currentPersona = blueprint.persona || 'balanced';
    weights = {
      w_h: blueprint.agent_weights?.w_h ?? 0.34,
      w_b: blueprint.agent_weights?.w_b ?? 0.33,
      w_t: blueprint.agent_weights?.w_t ?? 0.33,
    };
    render();
  } catch (err) {
    showError(err.message);
  }
}

// ── Submit Query ───────────────────────────────────────────────────────────
async function submitQuery(queryText) {
  const $status = document.getElementById('query-status');
  const $submit = document.getElementById('query-submit');
  const $input  = document.getElementById('query-input');

  $submit.disabled = true;
  $input.disabled = true;

  $status.className = 'query-status running';
  $status.textContent = '⟳ Listening to your cravings… finding the best matches…';

  showLoading();

  try {
    const formData = new FormData();
    formData.append('query', queryText || '');
    if (audioFile) formData.append('audio', audioFile);
    if (imageFile) formData.append('image', imageFile);

    const resp = await fetch(`${API_BASE}/submit`, { method: 'POST', body: formData });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: `Server responded ${resp.status}` }));
      throw new Error(err.detail || `Server responded ${resp.status}`);
    }

    blueprint = await resp.json();
    currentPersona = blueprint.persona || 'balanced';
    weights = {
      w_h: blueprint.agent_weights?.w_h ?? 0.34,
      w_b: blueprint.agent_weights?.w_b ?? 0.33,
      w_t: blueprint.agent_weights?.w_t ?? 0.33,
    };
    firstRenderDone = false;
    render();

    removeFile('audio');
    removeFile('image');

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

// ── Recalculate ────────────────────────────────────────────────────────────
async function recalculate() {
  try {
    const resp = await fetch(`${API_BASE}/recalculate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        w_health: parseFloat(weights.w_h.toFixed(3)),
        w_budget: parseFloat(weights.w_b.toFixed(3)),
        w_taste: parseFloat(weights.w_t.toFixed(3)),
        persona: currentPersona,
      }),
    });
    if (!resp.ok) throw new Error(`Server responded ${resp.status}`);
    blueprint = await resp.json();
    updateDynamic();
  } catch (err) {
    console.error('recalculate failed:', err);
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

// ── Utility Label Helpers ──────────────────────────────────────────────────
function healthLabel(v) { return v > 0.8 ? 'Excellent' : v > 0.5 ? 'Good' : 'Low'; }
function budgetLabel(v) { return v > 0.7 ? 'Great Value' : v > 0.4 ? 'Fair' : 'Pricey'; }
function tasteLabel(v) { return v > 0.8 ? 'Perfect Match' : v > 0.5 ? 'Good Match' : 'Mild Match'; }

// ── Full Render ────────────────────────────────────────────────────────────
function render() {
  if (!blueprint) return;
  showContent();

  const dish = blueprint.winning_dish || {};
  const scores = blueprint.utility_breakdown || {};
  const wts = blueprint.agent_weights || {};
  const traces = blueprint.xai_traces || [];
  const candidates = blueprint.all_candidate_scores || [];
  const context = blueprint.source_context || {};
  const personas = blueprint.personas_available || {};
  const fulfillment = blueprint.fulfillment || {};

  weights = { w_h: wts.w_h ?? 0.34, w_b: wts.w_b ?? 0.33, w_t: wts.w_t ?? 0.33 };

  $main.innerHTML = `
    ${renderContextBar(context)}
    ${renderPersonaBar(personas)}
    ${renderWinnerCard(dish, scores)}
    ${renderCtaRow(fulfillment)}
    <div class="controls-row">
      <div class="controls-left">
        ${renderScoresCard(scores)}
      </div>
      <div class="controls-right">
        ${renderSliderGroup(wts)}
      </div>
    </div>
    ${renderRestaurants(fulfillment)}
    ${renderCandidates(candidates, dish.dish_id)}
    ${renderXaiSection(traces)}
    <footer class="app-footer">
      Powered by <a href="#">FIPE Engine</a> — Graph Theory × Game Theory × Compiler Design
    </footer>
  `;

  bindPersonaChips();
  bindSliders();
  bindXaiToggle();
  bindCtaButtons(fulfillment);

  requestAnimationFrame(() => { firstRenderDone = true; $main.classList.add('rendered'); });
}

// ── Fast Update (sliders/persona) ──────────────────────────────────────────
function updateDynamic() {
  if (!blueprint) return;
  const dish = blueprint.winning_dish || {};
  const scores = blueprint.utility_breakdown || {};
  const traces = blueprint.xai_traces || [];
  const candidates = blueprint.all_candidate_scores || [];
  const fulfillment = blueprint.fulfillment || {};

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

  // Score bars
  updateScoreBar('health', scores.u_health, healthLabel);
  updateScoreBar('budget', scores.u_budget, budgetLabel);
  updateScoreBar('taste', scores.u_taste, tasteLabel);

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

function updateScoreBar(cls, value, labelFn) {
  const val = value ?? 0;
  const pct = (val * 100).toFixed(0);
  const $fill = document.querySelector(`.score-bar-fill.${cls}`);
  const $val = document.querySelector(`.score-value.${cls}`);
  const $label = document.querySelector(`.score-label-text.${cls}`);
  if ($fill) $fill.style.width = `${Math.min(val * 100, 100)}%`;
  if ($val) $val.textContent = `${pct}%`;
  if ($label) $label.textContent = labelFn(val);
}

// ── Bind Events ────────────────────────────────────────────────────────────
function bindPersonaChips() {
  document.querySelectorAll('.persona-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const key = chip.dataset.persona;
      currentPersona = key;
      // Highlight active
      document.querySelectorAll('.persona-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      // Get persona default weights from blueprint
      const personas = blueprint.personas_available || {};
      // We send recalculate with the new persona (backend applies weights)
      weights = { w_h: 0.34, w_b: 0.33, w_t: 0.33 }; // will be overridden by backend
      recalculate().then(() => {
        // Update slider positions from response
        if (blueprint) {
          const wts = blueprint.agent_weights || {};
          weights = { w_h: wts.w_h ?? 0.34, w_b: wts.w_b ?? 0.33, w_t: wts.w_t ?? 0.33 };
          const sh = document.getElementById('slider-health');
          const sb = document.getElementById('slider-budget');
          const st = document.getElementById('slider-taste');
          if (sh) { sh.value = weights.w_h; document.getElementById('slider-health-val').textContent = (weights.w_h * 100).toFixed(0) + '%'; }
          if (sb) { sb.value = weights.w_b; document.getElementById('slider-budget-val').textContent = (weights.w_b * 100).toFixed(0) + '%'; }
          if (st) { st.value = weights.w_t; document.getElementById('slider-taste-val').textContent = (weights.w_t * 100).toFixed(0) + '%'; }
        }
      });
    });
  });
}

function bindSliders() {
  const sliderIds = ['slider-health', 'slider-budget', 'slider-taste'];
  const keys = ['w_h', 'w_b', 'w_t'];

  sliderIds.forEach((id, idx) => {
    const slider = document.getElementById(id);
    if (!slider) return;

    slider.addEventListener('input', () => {
      const newVal = parseFloat(slider.value);
      const otherKeys = keys.filter((_, i) => i !== idx);
      const otherSum = otherKeys.reduce((s, k) => s + weights[k], 0);

      weights[keys[idx]] = newVal;

      // Proportionally adjust others to maintain sum = 1.0
      const remaining = 1.0 - newVal;
      if (otherSum > 0) {
        otherKeys.forEach(k => { weights[k] = (weights[k] / otherSum) * remaining; });
      } else {
        otherKeys.forEach(k => { weights[k] = remaining / otherKeys.length; });
      }

      // Update all slider positions and labels
      keys.forEach((k, i) => {
        const s = document.getElementById(sliderIds[i]);
        const v = document.getElementById(sliderIds[i] + '-val');
        if (s) s.value = weights[k];
        if (v) v.textContent = (weights[k] * 100).toFixed(0) + '%';
      });
    });

    slider.addEventListener('change', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => recalculate(), 150);
    });
  });
}

function bindXaiToggle() {
  const btn = document.getElementById('xai-toggle');
  if (!btn) return;
  btn.addEventListener('click', () => {
    xaiOpen = !xaiOpen;
    const panel = document.getElementById('xai-panel');
    const chevron = document.getElementById('xai-chevron');
    if (panel) panel.classList.toggle('open', xaiOpen);
    if (chevron) chevron.classList.toggle('open', xaiOpen);
  });
}

function bindCtaButtons(fulfillment) {
  const recipeBtn = document.getElementById('cta-recipe');
  if (recipeBtn) {
    recipeBtn.addEventListener('click', () => openRecipeModal(fulfillment.recipe));
  }
  const orderBtn = document.getElementById('cta-order');
  if (orderBtn) {
    orderBtn.addEventListener('click', () => {
      const section = document.getElementById('restaurants-section');
      if (section) {
        section.style.display = section.style.display === 'none' ? 'block' : 'none';
        section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  }
}

// ── Recipe Modal ───────────────────────────────────────────────────────────
function openRecipeModal(recipe) {
  if (!recipe) return;
  const $modal = document.getElementById('recipe-modal');
  const $content = document.getElementById('recipe-modal-content');

  const dish = blueprint?.winning_dish || {};
  const totalCost = (recipe.grocery_list || []).reduce((s, g) => s + (g.est_cost || 0), 0);

  $content.innerHTML = `
    <div class="recipe-header">
      <div class="recipe-header-top">
        <h2>🍳 ${dish.name || 'Recipe'}</h2>
        <button class="recipe-close" id="recipe-close-btn">✕</button>
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

  $modal.classList.add('open');
  document.body.style.overflow = 'hidden';

  document.getElementById('recipe-close-btn').addEventListener('click', closeRecipeModal);
}

function closeRecipeModal() {
  document.getElementById('recipe-modal').classList.remove('open');
  document.body.style.overflow = '';
}

// ── Render: Context Bar ────────────────────────────────────────────────────
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

// ── Render: Persona Bar ────────────────────────────────────────────────────
function renderPersonaBar(personas) {
  if (!personas || !Object.keys(personas).length) return '';
  const chips = Object.entries(personas).map(([key, p]) => {
    const active = key === currentPersona ? 'active' : '';
    return `<button class="persona-chip ${active}" data-persona="${key}">
      <span class="persona-icon">${p.icon}</span>
      <span class="persona-name">${p.display_name}</span>
    </button>`;
  }).join('');
  return `<div class="persona-bar"><div class="persona-scroll">${chips}</div></div>`;
}

// ── Render: Winner Card ────────────────────────────────────────────────────
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
      </div>
    </div>
  `;
}

// ── Render: CTA Row ────────────────────────────────────────────────────────
function renderCtaRow(fulfillment) {
  return `
    <div class="cta-row">
      <button class="cta-btn cta-recipe" id="cta-recipe">🍳 View Recipe</button>
      <button class="cta-btn cta-order" id="cta-order">🛵 Order Nearby</button>
    </div>
  `;
}

// ── Render: Scores Card ────────────────────────────────────────────────────
function renderScoresCard(scores) {
  const items = [
    { label: 'Healthy', key: 'u_health', cls: 'health', labelFn: healthLabel },
    { label: 'Affordable', key: 'u_budget', cls: 'budget', labelFn: budgetLabel },
    { label: 'Tasty', key: 'u_taste', cls: 'taste', labelFn: tasteLabel },
  ];
  const rows = items.map(item => {
    const val = scores[item.key] ?? 0;
    const pct = (val * 100).toFixed(0);
    const lab = item.labelFn(val);
    return `
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
    `;
  }).join('');
  return `<div class="scores-card"><h2><span>📊</span> How It Scores</h2>${rows}</div>`;
}

// ── Render: Slider Group ───────────────────────────────────────────────────
function renderSliderGroup(wts) {
  const sliders = [
    { id: 'slider-health', label: '💪 Health', key: 'w_h', cls: 'health' },
    { id: 'slider-budget', label: '💰 Budget', key: 'w_b', cls: 'budget' },
    { id: 'slider-taste',  label: '😋 Taste',  key: 'w_t', cls: 'taste' },
  ];
  const rows = sliders.map(s => {
    const val = wts[s.key] ?? 0.33;
    return `
      <div class="slider-row">
        <span class="slider-label">${s.label}</span>
        <input type="range" class="priority-slider ${s.cls}" id="${s.id}"
               min="0" max="1" step="0.01" value="${val}">
        <span class="slider-val" id="${s.id}-val">${(val * 100).toFixed(0)}%</span>
      </div>
    `;
  }).join('');
  return `<div class="slider-group"><h2><span>⚖️</span> Your Priorities</h2>${rows}</div>`;
}

// ── Render: Restaurants ────────────────────────────────────────────────────
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

// ── Render: Candidates ─────────────────────────────────────────────────────
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
    const tags = (c.human_tags || []).slice(0, 2).map(t => `<span class="tag-pill small">${t}</span>`).join('');
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

// ── Render: XAI Traces ─────────────────────────────────────────────────────
function renderXaiSection(traces) {
  if (!traces.length) return '';
  return `
    <div class="xai-section">
      <button class="xai-toggle" id="xai-toggle">
        <span class="xai-toggle-left"><span>⚙️</span> Developer Mode — AI Reasoning Trace</span>
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
function capitalize(str) { return str.charAt(0).toUpperCase() + str.slice(1); }
function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}
