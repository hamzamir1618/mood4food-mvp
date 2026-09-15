import { useState, useCallback } from 'react';

const STORAGE_KEY = 'mood4food_recents';
const MAX_RECENTS = 5;

function loadRecents() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

export function useRecent() {
  const [recents, setRecents] = useState(loadRecents);

  const addRecent = useCallback((query) => {
    if (!query || !query.trim()) return;
    const trimmed = query.trim();
    setRecents(prev => {
      const updated = [trimmed, ...prev.filter(r => r !== trimmed)].slice(0, MAX_RECENTS);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  return { recents, addRecent };
}
