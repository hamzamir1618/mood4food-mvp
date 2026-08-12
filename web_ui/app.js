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

  const form = document.getElementById('query-form');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = document.getElementById('query-input').value.trim();
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
    document.getElementById('audio-file').value = '';
    document.getElementById('audio-btn').classList.remove('has-file');
  } else {
    setImageFile(null);
    document.getElementById('image-file').value = '';
    document.getElementById('image-btn').classList.remove('has-file');
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
    ui.showError(getErrorMessage(err));
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
    updateBlueprint(bp);
    setFirstRenderDone(false);
    renderApp();

    removeFile('audio');
    removeFile('image');

    $status.className = 'query-status success';
    $status.textContent = `✓ Found ${bp.all_candidate_scores?.length ?? 0} options — recommending ${bp.winning_dish?.name || 'a dish'}`;
    setTimeout(() => { $status.textContent = ''; $status.className = 'query-status'; }, 4000);
  } catch (err) {
    const msg = getErrorMessage(err);
    ui.showToast(msg, 'error');
    $status.className = 'query-status error';
    $status.textContent = `✗ ${msg}`;
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

function bindPersonaChips() {
  document.querySelectorAll('.persona-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const key = chip.dataset.persona;
      setCurrentPersona(key);
      document.querySelectorAll('.persona-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');

      // Temporary weights before response
      setWeights({ w_h: 0.34, w_b: 0.33, w_t: 0.33 });
      
      recalculate().then(() => {
        if (state.blueprint) {
          const wts = state.blueprint.agent_weights || {};
          setWeights({ w_h: wts.w_h ?? 0.34, w_b: wts.w_b ?? 0.33, w_t: wts.w_t ?? 0.33 });
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
