import { useState, useCallback, useRef } from 'react';

export function useBlueprint() {
  const [blueprint, setBlueprint] = useState(null);
  const [currentPersona, setCurrentPersona] = useState('balanced');
  const [weights, setWeights] = useState({ w_h: 0.34, w_b: 0.33, w_t: 0.33 });
  const [xaiOpen, setXaiOpen] = useState(false);
  const [viewState, setViewState] = useState('empty'); // 'loading' | 'error' | 'empty' | 'content'
  const [errorMessage, setErrorMessage] = useState('');
  const rejectedIdsRef = useRef([]);

  const updateBlueprint = useCallback((bp) => {
    setBlueprint(bp);
    setCurrentPersona(bp?.persona || 'balanced');
    setWeights({
      w_h: bp?.agent_weights?.w_h ?? 0.34,
      w_b: bp?.agent_weights?.w_b ?? 0.33,
      w_t: bp?.agent_weights?.w_t ?? 0.33,
    });
  }, []);

  const resetRejected = useCallback(() => {
    rejectedIdsRef.current = [];
  }, []);

  const addRejected = useCallback((id) => {
    rejectedIdsRef.current.push(id);
  }, []);

  return {
    blueprint, setBlueprint,
    currentPersona, setCurrentPersona,
    weights, setWeights,
    xaiOpen, setXaiOpen,
    viewState, setViewState,
    errorMessage, setErrorMessage,
    updateBlueprint,
    rejectedIdsRef, resetRejected, addRejected,
  };
}
