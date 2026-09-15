import { capitalize } from '../utils.js';

export default function ContextBar({ sourceContext }) {
  if (!sourceContext) return null;
  const budget = sourceContext.budget_max_pkr || '—';
  const allergens = (sourceContext.allergens_pruned || []).join(', ') || 'None';
  const mood = sourceContext.mood_vector_seed || 'neutral';

  return (
    <div className="context-bar">
      <div className="context-chip">
        <span className="chip-icon">💰</span> Budget: <span className="chip-value">Rs. {budget}</span>
      </div>
      <div className="context-chip">
        <span className="chip-icon">🚫</span> Excluded: <span className="chip-value">{capitalize(allergens)}</span>
      </div>
      <div className="context-chip">
        <span className="chip-icon">🎯</span> Mood: <span className="chip-value">{capitalize(mood)}</span>
      </div>
    </div>
  );
}
