import { useRef, useCallback } from 'react';

export default function SliderGroup({ weights, onWeightsChange, onRecalculate, disabled }) {
  const debounceRef = useRef(null);

  const sliders = [
    { id: 'slider-health', label: '💪 Health', key: 'w_h', cls: 'health' },
    { id: 'slider-budget', label: '💰 Budget', key: 'w_b', cls: 'budget' },
    { id: 'slider-taste',  label: '😋 Taste',  key: 'w_t', cls: 'taste' },
  ];
  const keys = ['w_h', 'w_b', 'w_t'];

  const handleInput = useCallback((idx, newVal) => {
    const otherKeys = keys.filter((_, i) => i !== idx);
    const otherSum = otherKeys.reduce((s, k) => s + weights[k], 0);

    const newWeights = { ...weights };
    newWeights[keys[idx]] = newVal;

    const remaining = 1.0 - newVal;
    if (otherSum > 0) {
      otherKeys.forEach(k => { newWeights[k] = (weights[k] / otherSum) * remaining; });
    } else {
      otherKeys.forEach(k => { newWeights[k] = remaining / otherKeys.length; });
    }

    onWeightsChange(newWeights);

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => onRecalculate(), 300);
  }, [weights, onWeightsChange, onRecalculate]);

  return (
    <div className="slider-group">
      <h2><span>⚖️</span> Your Priorities</h2>
      {sliders.map((s, idx) => {
        const val = weights[s.key] ?? 0.33;
        return (
          <div key={s.id} className="slider-row">
            <span className="slider-label">{s.label}</span>
            <input
              type="range"
              className={`priority-slider ${s.cls}`}
              id={s.id}
              min="0"
              max="1"
              step="0.01"
              value={val}
              aria-label={`${s.label} Priority`}
              disabled={disabled}
              onChange={(e) => handleInput(idx, parseFloat(e.target.value))}
            />
            <span className="slider-val" id={`${s.id}-val`}>{(val * 100).toFixed(0)}%</span>
          </div>
        );
      })}
    </div>
  );
}
