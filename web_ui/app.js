/* ═══════════════════════════════════════════════════════════════════════════
   FIPE Mood4Food — Client-Side Logic v2
   Personas, multi-axis sliders, recipes, restaurants, image-heavy UI
   ═══════════════════════════════════════════════════════════════════════════ */

import * as api from './api.js';
import { state, updateBlueprint, setCurrentPersona, setWeights, setXaiOpen, setFirstRenderDone, setAudioFile, setImageFile } from './state.js';
import * as ui from './ui.js';

let debounceTimer = null;
let rejectedIds = [];

// Expose globals for inline event handlers in HTML
window.fetchBlueprint = fetchBlueprint;
window.removeFile = removeFile;

// ── Boot ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('refresh-btn').addEventListener('click', fetchBlueprint);
  
  try {
    const recents = JSON.parse(localStorage.getItem('mood4food_recents') || '[]');
    ui.renderRecentSearches(recents);
  } catch(e) {}

  const form = document.getElementById('query-form');
  let lastWarnedQuery = null;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = document.getElementById('query-input').value.trim();
    
    const budgetMatch = text.match(/(?:under|budget|max|below|for)\s*[a-z\s]*?(?:rs\.?\s*|rupees\s*)?(\d+)/i) || text.match(/(\d+)\s*(?:rs|rupees|pkr)/i);
    if (budgetMatch && !state.audioFile && !state.imageFile) {
      const parsedBudget = parseInt(budgetMatch[1], 10);
      if (parsedBudget > 0 && parsedBudget < 50 && text !== lastWarnedQuery) {
        let warningEl = document.getElementById('budget-warning');
        if (!warningEl) {
          warningEl = document.createElement('div');
          warningEl.id = 'budget-warning';
          warningEl.className = 'budget-warning';
          document.getElementById('query-bar').appendChild(warningEl);
        }
        warningEl.innerHTML = `⚠️ That budget (Rs. ${parsedBudget}) is very low — you may not get results. <a href="#" id="search-anyway-btn" style="color: var(--accent-budget); text-decoration: underline; margin-left: 8px;">Search anyway</a>`;
        
        document.getElementById('search-anyway-btn').addEventListener('click', (ev) => {
          ev.preventDefault();
          lastWarnedQuery = text;
          warningEl.remove();
          submitQuery(text);
        });

        lastWarnedQuery = text;
        return;
      }
    }

    const warningEl = document.getElementById('budget-warning');
    if (warningEl) warningEl.remove();
    lastWarnedQuery = null;

    if (text || state.audioFile || state.imageFile) submitQuery(text);
  });

  let mediaRecorder;
  let audioChunks = [];

  document.getElementById('audio-btn').addEventListener('click', async () => {
    const btn = document.getElementById('audio-btn');
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
      btn.textContent = '🎤';
      btn.style.color = '';
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = () => {
          const blob = new Blob(audioChunks, { type: 'audio/webm' });
          const file = new File([blob], 'recording.webm', { type: 'audio/webm' });
          setAudioFile(file);
          submitQuery('', 'Listening...');
          stream.getTracks().forEach(t => t.stop());
        };
        mediaRecorder.start();
        btn.textContent = '⏹';
        btn.style.color = '#EF4444'; // red recording state
      } catch (err) {
        console.error("Microphone error:", err);
        ui.showToast("Could not access microphone.", "error");
      }
    }
  });

  document.getElementById('image-btn').addEventListener('click', () => {
    document.getElementById('image-file').click();
  });

  document.getElementById('image-file').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      submitQuery('', 'Analyzing image...');
    }
  });

  // Recipe modal backdrop close
  document.getElementById('recipe-modal-backdrop').addEventListener('click', closeRecipeModal);

  fetchBlueprint();
});

function removeFile(type) {
  if (type === 'audio') {
    setAudioFile(null);
    const input = document.getElementById('audio-file');
    if (input) input.value = '';
    const btn = document.getElementById('audio-btn');
    if (btn) btn.classList.remove('has-file');
  } else {
    setImageFile(null);
    const input = document.getElementById('image-file');
    if (input) input.value = '';
    const btn = document.getElementById('image-btn');
    if (btn) btn.classList.remove('has-file');
  }
  ui.updateFileChips();
}

function getErrorMessage(err) {
  if (err.name === 'ApiError') {
    if (err.status === 429) return "You're doing that too fast! Please wait a moment.";
    if (err.status === 400) return typeof err.details?.detail === 'string' ? err.details.detail : "Invalid request. Please submit a query first.";
    if (err.status === 501) return "Try this in the local demo — see the video linked below";
    if (err.status >= 500) return "Our servers are currently overwhelmed. Please try again later.";
    return typeof err.details?.detail === 'string' ? err.details.detail : `Server error (${err.status})`;
  }
  return "Network error. Please check your connection.";
}

// ── Orchestration: Fetch Blueprint ─────────────────────────────────────────
async function fetchBlueprint() {
  ui.showLoading();
  setFirstRenderDone(false);
  try {
    const bp = await api.getFulfillment();
    updateBlueprint(bp);
    renderApp();
  } catch (err) {
    if (err.status === 404 || (err.message && err.message.toLowerCase().includes("decision blueprint"))) {
      ui.showEmptyState();
    } else {
      ui.showError(getErrorMessage(err));
    }
  }
}

// ── Orchestration: Submit Query ────────────────────────────────────────────
async function submitQuery(queryText, customLoadingMsg) {
  const $status = document.getElementById('query-status');
  const $submit = document.getElementById('query-submit');
  const $input  = document.getElementById('query-input');

  $submit.disabled = true;
  $input.disabled = true;

  $status.className = 'query-status running';
  $status.textContent = customLoadingMsg || '⟳ Listening to your cravings… finding the best matches…';

  ui.showLoading();
  ui.setUIEnabled(false);

  try {
    rejectedIds = []; // Reset on new query
    const formData = new FormData();
    formData.append('text', queryText || '');
    if (state.audioFile) formData.append('audio', state.audioFile);
    if (state.imageFile) formData.append('image', state.imageFile);

    const bp = await api.submitQuery(formData);
    
    // Save to recent searches if it's a text query
    if (queryText && queryText.trim()) {
      let recents = [];
      try { recents = JSON.parse(localStorage.getItem('mood4food_recents') || '[]'); } catch(e) {}
      recents = recents.filter(r => r !== queryText.trim());
      recents.unshift(queryText.trim());
      if (recents.length > 5) recents.pop();
      localStorage.setItem('mood4food_recents', JSON.stringify(recents));
      ui.renderRecentSearches(recents);
    }

    updateBlueprint(bp);
    setFirstRenderDone(false);
    renderApp();

    removeFile('audio');
    removeFile('image');

    $status.className = 'query-status success';
    $status.textContent = `✓ Found ${bp.candidate_count ?? 0} options — recommending ${bp.winning_dish?.name || 'a dish'}`;
    setTimeout(() => { $status.textContent = ''; $status.className = 'query-status'; }, 4000);
  } catch (err) {
    const msg = getErrorMessage(err);
    ui.showToast(msg, 'error');
    $status.textContent = '';
    $status.className = 'query-status';
    if (!state.blueprint) {
      ui.showError(msg);
    }
  } finally {
    $submit.disabled = false;
    $input.disabled = false;
    ui.setUIEnabled(true);
  }
}

// ── Orchestration: Recalculate ─────────────────────────────────────────────
async function recalculate() {
  ui.setUIEnabled(false);
  ui.setRecalcLoading(true);
  try {
    rejectedIds = []; // Reset on recalculate
    const bp = await api.recalculate({
      w_health: parseFloat(state.weights.w_h.toFixed(3)),
      w_budget: parseFloat(state.weights.w_b.toFixed(3)),
      w_taste: parseFloat(state.weights.w_t.toFixed(3)),
      persona: state.currentPersona,
    });
    updateBlueprint(bp);
    ui.updateDynamic();
    bindRunnersUp();
  } catch (err) {
    console.error('recalculate failed:', err);
    ui.showToast(getErrorMessage(err), 'error');
  } finally {
    ui.setUIEnabled(true);
    ui.setRecalcLoading(false);
  }
}

// ── Render & Bind ──────────────────────────────────────────────────────────
function renderApp() {
  ui.render();
  bindPersonaChips();
  bindSliders();
  bindXaiToggle();
  bindCtaButtons();
  bindAlternateBtn();
  bindRunnersUp();
  requestAnimationFrame(() => { 
    setFirstRenderDone(true);
    ui.$main.classList.add('rendered'); 
  });
}

function animateSlider(sliderId, targetValue) {
  const slider = document.getElementById(sliderId);
  const valDisplay = document.getElementById(sliderId + '-val');
  if (!slider) return;
  const startValue = parseFloat(slider.value) || 0;
  const duration = 400; // 400ms for a visible smooth slide
  const startTime = performance.now();

  function step(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const currentVal = startValue + (targetValue - startValue) * easeProgress;
    slider.value = currentVal;
    if (valDisplay) valDisplay.textContent = (currentVal * 100).toFixed(0) + '%';
    
    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      slider.value = targetValue;
      if (valDisplay) valDisplay.textContent = (targetValue * 100).toFixed(0) + '%';
    }
  }
  requestAnimationFrame(step);
}

function bindPersonaChips() {
  document.querySelectorAll('.persona-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const key = chip.dataset.persona;
      setCurrentPersona(key);
      document.querySelectorAll('.persona-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');

      const personasAvailable = state.blueprint?.personas_available || {};
      const personaData = personasAvailable[key];

      if (personaData) {
        ui.showToast(personaData.description || `Switched to ${personaData.display_name}`, 'info');
        const targetWts = personaData.weights || { w_health: 0.34, w_budget: 0.33, w_taste: 0.33 };
        
        // Visibly animate sliders to the new weights immediately
        animateSlider('slider-health', targetWts.w_health);
        animateSlider('slider-budget', targetWts.w_budget);
        animateSlider('slider-taste', targetWts.w_taste);
      }
      
      recalculate().then(() => {
        if (state.blueprint) {
          const wts = state.blueprint.agent_weights || {};
          setWeights({ w_h: wts.w_h ?? 0.34, w_b: wts.w_b ?? 0.33, w_t: wts.w_t ?? 0.33 });
          // Ensure they are synced to the backend's final values, snapping is fine here 
          // because they should match the animated targets very closely
          const sh = document.getElementById('slider-health');
          const sb = document.getElementById('slider-budget');
          const st = document.getElementById('slider-taste');
          if (sh) { sh.value = state.weights.w_h; document.getElementById('slider-health-val').textContent = (state.weights.w_h * 100).toFixed(0) + '%'; }
          if (sb) { sb.value = state.weights.w_b; document.getElementById('slider-budget-val').textContent = (state.weights.w_b * 100).toFixed(0) + '%'; }
          if (st) { st.value = state.weights.w_t; document.getElementById('slider-taste-val').textContent = (state.weights.w_t * 100).toFixed(0) + '%'; }
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
      const otherSum = otherKeys.reduce((s, k) => s + state.weights[k], 0);

      const newWeights = { ...state.weights };
      newWeights[keys[idx]] = newVal;

      const remaining = 1.0 - newVal;
      if (otherSum > 0) {
        otherKeys.forEach(k => { newWeights[k] = (state.weights[k] / otherSum) * remaining; });
      } else {
        otherKeys.forEach(k => { newWeights[k] = remaining / otherKeys.length; });
      }

      setWeights(newWeights);

      keys.forEach((k, i) => {
        const s = document.getElementById(sliderIds[i]);
        const v = document.getElementById(sliderIds[i] + '-val');
        if (s) s.value = state.weights[k];
        if (v) v.textContent = (state.weights[k] * 100).toFixed(0) + '%';
      });

      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => recalculate(), 300);
    });
  });
}

function bindXaiToggle() {
  const btn = document.getElementById('xai-toggle');
  if (!btn) return;
  btn.addEventListener('click', () => {
    setXaiOpen(!state.xaiOpen);
    const panel = document.getElementById('xai-panel');
    const chevron = document.getElementById('xai-chevron');
    if (panel) panel.classList.toggle('open', state.xaiOpen);
    if (chevron) chevron.classList.toggle('open', state.xaiOpen);
  });
}

function bindCtaButtons() {
  const fulfillment = state.blueprint?.fulfillment || {};
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

function bindRunnersUp() {
  document.querySelectorAll('.runner-card').forEach(card => {
    // Prevent multiple bindings if we call this in updateDynamic
    card.removeEventListener('click', toggleRunner);
    card.addEventListener('click', toggleRunner);
  });
}
function toggleRunner(e) {
  this.classList.toggle('expanded');
}

function bindAlternateBtn() {
  const btn = document.getElementById('btn-alternate');
  if (btn) {
    btn.removeEventListener('click', fetchAlternate);
    btn.addEventListener('click', fetchAlternate);
  }
}

async function fetchAlternate() {
  const currentWinner = state.blueprint?.winning_dish?.dish_id;
  if (!currentWinner) return;

  rejectedIds.push(currentWinner);
  ui.setUIEnabled(false);
  ui.setRecalcLoading(true);

  try {
    const bp = await api.getAlternate(rejectedIds);
    if (bp.no_more_alternates) {
      const btn = document.getElementById('btn-alternate');
      if (btn) {
        btn.disabled = true;
        btn.textContent = "That's everything that matched — try adjusting your sliders or persona instead";
      }
    } else {
      updateBlueprint(bp);
      renderApp();
    }
  } catch (err) {
    console.error('Alternate failed:', err);
    ui.showToast(getErrorMessage(err), 'error');
  } finally {
    ui.setUIEnabled(true);
    ui.setRecalcLoading(false);
  }
}

// ── Orchestration: Recipe Modal ────────────────────────────────────────────
function openRecipeModal(recipe) {
  if (!recipe) return;
  const $modal = document.getElementById('recipe-modal');
  const $content = document.getElementById('recipe-modal-content');

  $content.innerHTML = ui.renderRecipeModalContent(recipe);
  $modal.classList.add('open');
  document.body.style.overflow = 'hidden';

  // Note: the recipe-close-btn is dynamically created by renderRecipeModalContent
  document.getElementById('recipe-close-btn').addEventListener('click', closeRecipeModal);
}

function closeRecipeModal() {
  document.getElementById('recipe-modal').classList.remove('open');
  document.body.style.overflow = '';
}
