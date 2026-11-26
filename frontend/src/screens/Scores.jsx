import { useEffect, useState } from 'react';
import { allergenLine, joinList, matchOf, pct, scoreRows } from '../utils.js';

/**
 * How the pick scored: confidence-weighted MCDA breakdown.
 * Shows each term's raw utility, data confidence, weight, and effective shrunk value
 * (c · u + (1 - c) · 50) so the aggregation is inspectable rather than opaque.
 */
export default function Scores({ blueprint, onClose }) {
  const dish = blueprint?.winning_dish || {};
  const rows = scoreRows(blueprint);
  const coverage = dish.coverage != null ? pct(dish.coverage) : null;
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
          <div className="lab accent">How it scored · Confidence-weighted MCDA</div>
          <button className="lab lab-sm muted" onClick={onClose}>
            Close ✕
          </button>
        </div>
        <div className="h3 pt-8">{dish.name}</div>
        <div className="between pt-8">
          <div>
            <div className="lab lab-sm muted">Overall match</div>
            {coverage !== null && (
              <div className="small muted" style={{ marginTop: 2 }}>
                Data coverage {coverage}% · uncertain terms shrink toward 50
              </div>
            )}
          </div>
          <div className="bod-b" style={{ fontSize: 40 }}>{matchOf(blueprint)}</div>
        </div>

        {rows.map((row) => (
          <div key={row.key || row.label} style={{ borderTop: '1px solid var(--rule)', padding: '12px 0' }}>
            <div className="between">
              <div>
                <div className="lab">{row.label}</div>
                <div className="score-meta lab-sm muted">
                  {row.weight && <span>w = {row.weight}</span>}
                  <span>{row.confidence}% data conf.</span>
                  {row.confidence < 100 && <span>→ {row.effective} effective</span>}
                </div>
              </div>
              <div className="bod-b" style={{ fontSize: 28 }}>{row.value}</div>
            </div>
            <div className="bar bar-mcda is-accent" style={{ margin: '8px 0 10px' }}>
              <span
                style={{
                  width: `${grown ? row.effective : 0}%`,
                  transition: 'width 760ms var(--ease)',
                }}
              />
              <i className="bar-neutral-tick" title="Neutral prior (50)" />
            </div>
            {row.text && <div className="body-serif">{row.text}</div>}
          </div>
        ))}

        {dish.reasons?.novelty && (
          <div style={{ borderTop: '1px solid var(--rule)', padding: '10px 0' }}>
            <div className="lab lab-sm muted">Novelty adjustment</div>
            <div className="small" style={{ marginTop: 4 }}>{dish.reasons.novelty}</div>
          </div>
        )}

        {dish.reasons?.peers && (
          <div style={{ borderTop: '1px solid var(--rule)', padding: '10px 0' }}>
            <div className="lab lab-sm muted">Similar-taste peer pull</div>
            <div className="small" style={{ marginTop: 4 }}>{dish.reasons.peers}</div>
          </div>
        )}

        <div style={{ borderTop: '1px solid var(--rule)', paddingTop: 12 }}>
          <div className="small" style={{ fontWeight: 700 }}>{allergenLine(dish.allergens)}</div>
          {dish.ingredients?.length > 0 && (
            <div className="small pt-8">Made with {joinList(dish.ingredients)}.</div>
          )}
          <div className="lab lab-sm muted pt-12" style={{ lineHeight: 1.6 }}>
            Formula: Σ wₖ · [cₖ · uₖ + (1 − cₖ) · 50] / Σ wₖ. Nutrition and allergens are
            estimated from typical ingredients; the restaurant hasn't confirmed them.
          </div>
        </div>

        <button className="btn btn-line" style={{ marginTop: 18 }} onClick={onClose}>
          <span className="lab">Done</span>
        </button>
      </div>
    </>
  );
}
