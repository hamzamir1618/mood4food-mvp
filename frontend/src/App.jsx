import { useEffect, useCallback, useState, useRef } from 'react';
import { useBlueprint } from './hooks/useBlueprint.js';
import { useRecent } from './hooks/useRecent.js';
import { useToast } from './components/Toast.jsx';
import * as api from './api.js';
import { getErrorMessage } from './utils.js';

import Header from './components/Header.jsx';
import QueryBar from './components/QueryBar.jsx';
import LoadingState from './components/LoadingState.jsx';
import EmptyState from './components/EmptyState.jsx';
import ErrorState from './components/ErrorState.jsx';
import ContextBar from './components/ContextBar.jsx';
import PersonaBar from './components/PersonaBar.jsx';
import RelaxationNotice from './components/RelaxationNotice.jsx';
import WinnerCard from './components/WinnerCard.jsx';
import RunnersUp from './components/RunnersUp.jsx';
import CtaRow from './components/CtaRow.jsx';
import ScoresCard from './components/ScoresCard.jsx';
import SliderGroup from './components/SliderGroup.jsx';
import RestaurantsSection from './components/RestaurantsSection.jsx';
import XaiSection from './components/XaiSection.jsx';
import RecipeModal from './components/RecipeModal.jsx';
import RecalcLoading from './components/RecalcLoading.jsx';

export default function App() {
  const {
    blueprint,
    currentPersona, setCurrentPersona,
    weights, setWeights,
    xaiOpen, setXaiOpen,
    viewState, setViewState,
    errorMessage, setErrorMessage,
    updateBlueprint,
    rejectedIdsRef, resetRejected, addRejected,
  } = useBlueprint();

  const { recents, addRecent } = useRecent();
  const showToast = useToast();

  const [uiDisabled, setUiDisabled] = useState(false);
  const [recalcLoading, setRecalcLoading] = useState(false);
  const [recipeOpen, setRecipeOpen] = useState(false);
  const [alternateDisabled, setAlternateDisabled] = useState(false);
  const [alternateText, setAlternateText] = useState('Not quite — show me something else');
  const restaurantsSectionRef = useRef(null);

  // ── Fetch Blueprint (cold load / refresh) ─────────────────────────────
  const fetchBlueprint = useCallback(async () => {
    setViewState('loading');
    try {
      const bp = await api.getFulfillment();
      updateBlueprint(bp);
      setViewState('content');
    } catch (err) {
      if (err.status === 404 || (err.message && err.message.toLowerCase().includes("decision blueprint"))) {
        setViewState('empty');
      } else {
        setErrorMessage(getErrorMessage(err));
        setViewState('error');
      }
    }
  }, [updateBlueprint, setViewState, setErrorMessage]);

  // Boot
  useEffect(() => {
    fetchBlueprint();
  }, [fetchBlueprint]);

  // ── Submit Query ──────────────────────────────────────────────────────
  const handleSubmit = useCallback(async (queryText, audioFile, imageFile, customLoadingMsg, controls) => {
    const { setStatusText, setStatusClass, setInputDisabled } = controls;

    setInputDisabled(true);
    setStatusClass('query-status running');
    setStatusText(customLoadingMsg || '⟳ Listening to your cravings… finding the best matches…');
    setViewState('loading');
    setUiDisabled(true);

    try {
      resetRejected();
      setAlternateDisabled(false);
      setAlternateText('Not quite — show me something else');

      const formData = new FormData();
      formData.append('text', queryText || '');
      if (audioFile) formData.append('audio', audioFile);
      if (imageFile) formData.append('image', imageFile);

      const bp = await api.submitQuery(formData);

      if (queryText && queryText.trim()) {
        addRecent(queryText);
      }

      updateBlueprint(bp);
      setViewState('content');

      setStatusClass('query-status success');
      setStatusText(`✓ Found ${bp.candidate_count ?? 0} options — recommending ${bp.winning_dish?.name || 'a dish'}`);
      setTimeout(() => { setStatusText(''); setStatusClass('query-status'); }, 4000);
    } catch (err) {
      const msg = getErrorMessage(err);
      showToast(msg, 'error');
      setStatusText('');
      setStatusClass('query-status');
      if (!blueprint) {
        setErrorMessage(msg);
        setViewState('error');
      }
    } finally {
      setInputDisabled(false);
      setUiDisabled(false);
    }
  }, [blueprint, updateBlueprint, resetRejected, addRecent, showToast, setViewState, setErrorMessage]);

  // ── Recalculate ───────────────────────────────────────────────────────
  const doRecalculate = useCallback(async () => {
    setUiDisabled(true);
    setRecalcLoading(true);
    try {
      resetRejected();
      setAlternateDisabled(false);
      setAlternateText('Not quite — show me something else');
      const bp = await api.recalculate({
        w_health: parseFloat(weights.w_h.toFixed(3)),
        w_budget: parseFloat(weights.w_b.toFixed(3)),
        w_taste: parseFloat(weights.w_t.toFixed(3)),
        persona: currentPersona,
      });
      updateBlueprint(bp);
    } catch (err) {
      console.error('recalculate failed:', err);
      showToast(getErrorMessage(err), 'error');
    } finally {
      setUiDisabled(false);
      setRecalcLoading(false);
    }
  }, [weights, currentPersona, updateBlueprint, resetRejected, showToast]);

  // ── Persona Select ────────────────────────────────────────────────────
  const handlePersonaSelect = useCallback(async (key) => {
    setCurrentPersona(key);
    const personasAvailable = blueprint?.personas_available || {};
    const personaData = personasAvailable[key];

    if (personaData) {
      showToast(personaData.description || `Switched to ${personaData.display_name}`, 'info');
      const targetWts = personaData.weights || { w_health: 0.34, w_budget: 0.33, w_taste: 0.33 };
      // Set weights to persona target weights immediately (React handles the visual update)
      setWeights({
        w_h: targetWts.w_health,
        w_b: targetWts.w_budget,
        w_t: targetWts.w_taste,
      });
    }

    // Trigger recalculate
    setUiDisabled(true);
    setRecalcLoading(true);
    try {
      resetRejected();
      setAlternateDisabled(false);
      setAlternateText('Not quite — show me something else');
      const bp = await api.recalculate({
        w_health: personaData?.weights?.w_health ?? 0.34,
        w_budget: personaData?.weights?.w_budget ?? 0.33,
        w_taste: personaData?.weights?.w_taste ?? 0.33,
        persona: key,
      });
      updateBlueprint(bp);
    } catch (err) {
      console.error('recalculate failed:', err);
      showToast(getErrorMessage(err), 'error');
    } finally {
      setUiDisabled(false);
      setRecalcLoading(false);
    }
  }, [blueprint, setCurrentPersona, setWeights, updateBlueprint, resetRejected, showToast]);

  // ── Alternate / Re-roll ───────────────────────────────────────────────
  const handleAlternate = useCallback(async () => {
    const currentWinner = blueprint?.winning_dish?.dish_id;
    if (!currentWinner) return;

    addRejected(currentWinner);
    setUiDisabled(true);
    setRecalcLoading(true);

    try {
      const bp = await api.getAlternate(rejectedIdsRef.current);
      if (bp.no_more_alternates) {
        setAlternateDisabled(true);
        setAlternateText("That's everything that matched — try adjusting your sliders or persona instead");
      } else {
        updateBlueprint(bp);
      }
    } catch (err) {
      console.error('Alternate failed:', err);
      showToast(getErrorMessage(err), 'error');
    } finally {
      setUiDisabled(false);
      setRecalcLoading(false);
    }
  }, [blueprint, addRejected, rejectedIdsRef, updateBlueprint, showToast]);

  // ── CTA Handlers ──────────────────────────────────────────────────────
  const handleRecipeClick = useCallback(() => {
    setRecipeOpen(true);
  }, []);

  const handleOrderClick = useCallback(() => {
    const section = restaurantsSectionRef.current;
    if (section) {
      const el = section.querySelector('#restaurants-section');
      if (el) {
        el.style.display = el.style.display === 'none' ? 'block' : 'none';
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, []);

  const handleRecentClick = useCallback((text) => {
    // Programmatically submit a recent search
    handleSubmit(text, null, null, null, {
      setStatusText: () => {},
      setStatusClass: () => {},
      setInputDisabled: () => {},
    });
  }, [handleSubmit]);

  // ── Derived data ──────────────────────────────────────────────────────
  const dish = blueprint?.winning_dish || {};
  const scores = blueprint?.utility_breakdown || {};
  const traces = blueprint?.xai_traces || [];
  const context = blueprint?.source_context || {};
  const personas = blueprint?.personas_available || {};
  const fulfillment = blueprint?.fulfillment || {};
  const hasWinner = dish && dish.dish_id;

  return (
    <>
      <Header onRefresh={fetchBlueprint} />

      <QueryBar onSubmit={handleSubmit} disabled={uiDisabled} />

      <div className="app-container">
        {viewState === 'loading' && <LoadingState />}
        {viewState === 'empty' && <EmptyState recents={recents} onRecentClick={handleRecentClick} />}
        {viewState === 'error' && <ErrorState message={errorMessage} onRetry={fetchBlueprint} />}
        {viewState === 'content' && (
          <div className={`main-content ${uiDisabled ? 'ui-disabled' : ''}`} id="main-content" style={{ display: 'flex' }}>
            <ContextBar sourceContext={context} />
            <PersonaBar
              personas={personas}
              currentPersona={currentPersona}
              onSelect={handlePersonaSelect}
            />

            {hasWinner ? (
              <>
                <RelaxationNotice notice={blueprint.relaxation_notice} />
                <WinnerCard
                  dish={dish}
                  scores={scores}
                  traces={traces}
                  onAlternate={handleAlternate}
                  alternateDisabled={alternateDisabled}
                  alternateText={alternateText}
                />
                <div id="runners-up-container">
                  <RunnersUp candidates={blueprint.top_candidates} winnerId={dish.dish_id} />
                </div>
                <CtaRow onRecipe={handleRecipeClick} onOrder={handleOrderClick} />
                <div className="controls-row">
                  <div className="controls-left">
                    <ScoresCard scores={scores} traces={traces} dish={dish} />
                  </div>
                  <div className="controls-right">
                    <SliderGroup
                      weights={weights}
                      onWeightsChange={setWeights}
                      onRecalculate={doRecalculate}
                      disabled={uiDisabled}
                    />
                  </div>
                </div>
                <div ref={restaurantsSectionRef}>
                  <RestaurantsSection fulfillment={fulfillment} dish={dish} />
                </div>
              </>
            ) : (
              <>
                <div className="empty-state-container">
                  <div className="empty-state-icon">🍽️</div>
                  <h3>No exact matches found</h3>
                  <p>We couldn't find a dish that strictly meets your requirements.<br />Try loosening your budget or switching up the persona sliders below!</p>
                </div>
                <div className="controls-row" style={{ justifyContent: 'center', maxWidth: 600, margin: '40px auto 20px' }}>
                  <div className="controls-right" style={{ width: '100%' }}>
                    <SliderGroup
                      weights={weights}
                      onWeightsChange={setWeights}
                      onRecalculate={doRecalculate}
                      disabled={uiDisabled}
                    />
                  </div>
                </div>
              </>
            )}
            <XaiSection traces={traces} open={xaiOpen} onToggle={() => setXaiOpen(!xaiOpen)} />
            <footer className="app-footer">
              Powered by <a href="#">FIPE Engine</a> — Graph Theory × Game Theory × Compiler Design
            </footer>
          </div>
        )}
      </div>

      <RecipeModal
        recipe={fulfillment.recipe}
        dish={dish}
        open={recipeOpen}
        onClose={() => setRecipeOpen(false)}
      />

      <RecalcLoading visible={recalcLoading} />
    </>
  );
}
