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
 *
 * `tasteUnset`: no flavour was asked for and none is known yet, so taste has nothing to rank
 * by (the server leaves it out). Its slider is shown but off, and says what would turn it on.
 */
export default function Weights({ weights, onChange, busy, tasteUnset = false }) {
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
      const rest = TERMS.map(([k]) => k).filter(
        (k) => k !== key && !(tasteUnset && k === 'w_taste'),
      );
      const restSum = rest.reduce((sum, k) => sum + (local[k] ?? 0), 0);
      const left = 1 - value;
      const next = { ...local, [key]: value, ...(tasteUnset ? { w_taste: 0 } : {}) };
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
    [local, onChange, tasteUnset],
  );

  // With taste off, budget and health are shown as shares of what they split between them.
  const others = tasteUnset ? 1 - (local.w_taste ?? 0) : 1;
  const shown = (key) => pct(others > 0 ? (local[key] ?? 0) / others : 0);

  return (
    <div className="weights">
      <div className="between">
        <div className="lab accent">What counts most</div>
        <div className="lab lab-sm muted">Re-ranks instantly</div>
      </div>
      {TERMS.map(([key, label]) => {
        const off = tasteUnset && key === 'w_taste';
        return (
          <label className={`weight${off ? ' is-off' : ''}`} key={key}>
            <span className="lab lab-sm">{label}</span>
            <input
              type="range"
              min="0"
              max="100"
              value={off ? 0 : shown(key)}
              disabled={busy || off}
              aria-label={`How much ${label.toLowerCase()} counts`}
              aria-describedby={off ? 'taste-unset' : undefined}
              onChange={(e) => move(key, Number(e.target.value) / 100)}
            />
            <span className="bod-b weight-value">{off ? '—' : shown(key)}</span>
          </label>
        );
      })}
      {tasteUnset && (
        <p id="taste-unset" className="small muted weights-note">
          No flavour to go on yet. Ask for one (spicy, sweet, sour) or choose dishes you like, and
          taste will count.
        </p>
      )}
    </div>
  );
}
