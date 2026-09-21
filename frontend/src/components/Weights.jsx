import { useCallback, useEffect, useRef, useState } from 'react';
import { pct } from '../utils.js';

const TERMS = [
  ['w_taste', 'Your taste'],
  ['w_budget', 'Budget'],
  ['w_health', 'Health'],
];
const SETTLE_MS = 350; // one request per gesture, not one per pixel
const EVEN = 1 / 3;

/** The blueprint reports weights as w_h/w_b/w_t; /recalculate takes the long names. */
const read = (w) => ({
  w_taste: w?.w_taste ?? w?.w_t ?? EVEN,
  w_budget: w?.w_budget ?? w?.w_b ?? EVEN,
  w_health: w?.w_health ?? w?.w_h ?? EVEN,
});

/**
 * What counts most, as three weights that always sum to 1: moving one takes its share from
 * the other two. Changing them re-ranks the dishes the query already found, so the pick can
 * change in front of you without another search.
 */
export default function Weights({ weights, onChange, busy }) {
  const [local, setLocal] = useState(() => read(weights));
  const timer = useRef(null);
  const dirty = useRef(false);

  // Follow the server's weights until the user takes over, then leave their hands alone.
  useEffect(() => {
    if (!dirty.current) setLocal(read(weights));
  }, [weights]);

  useEffect(() => () => clearTimeout(timer.current), []);

  const move = useCallback(
    (key, value) => {
      const rest = TERMS.map(([k]) => k).filter((k) => k !== key);
      const restSum = rest.reduce((sum, k) => sum + (local[k] ?? 0), 0);
      const left = 1 - value;
      const next = { ...local, [key]: value };
      rest.forEach((k) => {
        next[k] = restSum > 0 ? ((local[k] ?? 0) / restSum) * left : left / rest.length;
      });
      dirty.current = true;
      setLocal(next);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        dirty.current = false;
        onChange(next);
      }, SETTLE_MS);
    },
    [local, onChange],
  );

  return (
    <div className="weights">
      <div className="between">
        <div className="lab accent">What counts most</div>
        <div className="lab lab-sm muted">Re-ranks instantly</div>
      </div>
      {TERMS.map(([key, label]) => (
        <label className="weight" key={key}>
          <span className="lab lab-sm">{label}</span>
          <input
            type="range"
            min="0"
            max="100"
            value={pct(local[key])}
            disabled={busy}
            aria-label={`How much ${label.toLowerCase()} counts`}
            onChange={(e) => move(key, Number(e.target.value) / 100)}
          />
          <span className="bod-b weight-value">{pct(local[key])}</span>
        </label>
      ))}
    </div>
  );
}
