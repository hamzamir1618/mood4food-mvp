import { useEffect, useState } from 'react';
import { allergenLine, joinList, matchOf, scoreRows } from '../utils.js';

/** How the pick scored: one bar per term, each with the sentence behind it. */
export default function Scores({ blueprint, onClose }) {
  const dish = blueprint?.winning_dish || {};
  const rows = scoreRows(blueprint);
  const [grown, setGrown] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setGrown(true));
    return () => cancelAnimationFrame(id);
  }, []);

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className="sheet" role="dialog" aria-label="How it scored">
        <div className="between">
          <div className="lab accent">How it scored</div>
          <button className="lab lab-sm muted" onClick={onClose}>
            Close ✕
          </button>
        </div>
        <div className="h3 pt-8">{dish.name}</div>
        <div className="between pt-8">
          <div className="lab lab-sm muted">Overall</div>
          <div className="bod-b" style={{ fontSize: 40 }}>{matchOf(blueprint)}</div>
        </div>

        {rows.map((row) => (
          <div key={row.label} style={{ borderTop: '1px solid var(--rule)', padding: '12px 0' }}>
            <div className="between">
              <div className="lab">{row.label}</div>
              <div className="bod-b" style={{ fontSize: 28 }}>{row.value}</div>
            </div>
            <div className="bar is-accent" style={{ margin: '8px 0 10px' }}>
              <span style={{ width: `${grown ? row.value : 0}%`, transition: 'width 760ms var(--ease)' }} />
            </div>
            {row.text && <div className="body-serif">{row.text}</div>}
          </div>
        ))}

        <div style={{ borderTop: '1px solid var(--rule)', paddingTop: 12 }}>
          <div className="small" style={{ fontWeight: 700 }}>{allergenLine(dish.allergens)}</div>
          {dish.ingredients?.length > 0 && (
            <div className="small pt-8">Made with {joinList(dish.ingredients)}.</div>
          )}
          <div className="lab lab-sm muted pt-12" style={{ lineHeight: 1.6 }}>
            Nutrition and allergens are estimated from typical ingredients. The restaurant hasn't
            confirmed them.
          </div>
        </div>

        <button className="btn btn-line" style={{ marginTop: 18 }} onClick={onClose}>
          <span className="lab">Done</span>
        </button>
      </div>
    </>
  );
}
