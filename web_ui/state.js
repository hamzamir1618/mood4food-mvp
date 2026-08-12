export const state = {
  blueprint: null,
  currentPersona: 'balanced',
  weights: { w_h: 0.34, w_b: 0.33, w_t: 0.33 },
  xaiOpen: false,
  recipeOpen: false,
  firstRenderDone: false,
  audioFile: null,
  imageFile: null
};

export function updateBlueprint(bp) {
  state.blueprint = bp;
  state.currentPersona = bp?.persona || 'balanced';
  state.weights = {
    w_h: bp?.agent_weights?.w_h ?? 0.34,
    w_b: bp?.agent_weights?.w_b ?? 0.33,
    w_t: bp?.agent_weights?.w_t ?? 0.33,
  };
}

export function setCurrentPersona(p) { state.currentPersona = p; }
export function setWeights(w) { state.weights = w; }
export function setXaiOpen(o) { state.xaiOpen = o; }
export function setFirstRenderDone(d) { state.firstRenderDone = d; }
export function setAudioFile(f) { state.audioFile = f; }
export function setImageFile(f) { state.imageFile = f; }
