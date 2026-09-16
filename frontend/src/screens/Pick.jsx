import { useEffect, useRef, useState } from 'react';
import { allergenLine, matchOf, placeLine, rupees, scoreRows, serves } from '../utils.js';

const SWIPE = 110;

/** Counts a number up once per value change, so the match lands rather than appears. */
function useCountUp(target, ms = 900) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min(1, (now - start) / ms);
      setShown(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return shown;
}

export default function Pick({ blueprint, refinements, onRefine, onNext, onChoose, onScores, busy, rank }) {
  const dish = blueprint?.winning_dish || {};
  const match = matchOf(blueprint);
  const shown = useCountUp(match);
  const reasons = scoreRows(blueprint);
  const [dx, setDx] = useState(0);
  const [imageFailed, setImageFailed] = useState(false);
  const drag = useRef({ on: false, x: 0, moved: false });

  const down = (e) => {
    if (e.target.closest('[data-nodrag]')) return;
    drag.current = { on: true, x: e.clientX, moved: false };
    e.currentTarget.setPointerCapture?.(e.pointerId);
  };
  const move = (e) => {
    if (!drag.current.on) return;
    const next = e.clientX - drag.current.x;
    if (Math.abs(next) > 6) drag.current.moved = true;
    setDx(next);
  };
  const up = () => {
    if (!drag.current.on) return;
    const travelled = dx;
    drag.current.on = false;
    setDx(0);
    if (busy) return;
    if (travelled > SWIPE) onChoose();
    else if (travelled < -SWIPE) onNext();
  };

  return (
    <div className="screen">
      <div className="between pt-12">
        <div className="lab accent">The pick · {rank}</div>
        <div className="lab lab-sm muted">Swipe for the next dish</div>
      </div>
      <div className="rule-thick draw" style={{ marginTop: 8 }} />

      <div
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerCancel={up}
        style={{
          touchAction: 'pan-y',
          cursor: 'grab',
          transform: `translateX(${dx}px) rotate(${(dx / 40).toFixed(2)}deg)`,
          transition: drag.current.on ? 'none' : 'transform 300ms var(--ease)',
        }}
      >
        <div className="match-row">
          <div className="match-num">{shown}</div>
          <div style={{ paddingTop: 8 }}>
            <div className="lab">Match</div>
            <div className="lab lab-sm muted">Out of 100</div>
          </div>
          <div className="grow" />
          <button className="lab accent" data-nodrag="1" onClick={onScores} style={{ paddingTop: 8, textAlign: 'right' }}>
            The scores
            <br />
            <span className="bod" style={{ fontSize: 16 }}>↓</span>
          </button>
        </div>

        <h2 className="h2 mask pt-8">{dish.name}</h2>
        <div className="lab rise pt-12">{placeLine(dish)}</div>

        <div className="rule draw" style={{ marginTop: 10 }} />
        <div className="between" style={{ padding: '8px 0' }}>
          <div className="bod-b" style={{ fontSize: 32 }}>{rupees(dish.price_pkr)}</div>
          <div className="lab lab-sm muted">{serves(dish.serves_min, dish.serves_max)}</div>
        </div>
        <div className="rule draw" />

        {dish.image_url && !imageFailed && (
          <>
            <div className="photo wipe" style={{ height: 150, marginTop: 12 }}>
              <img src={dish.image_url} alt={dish.name} draggable="false" onError={() => setImageFailed(true)} />
            </div>
            {dish.is_rep_image && <div className="lab lab-sm muted pt-8">Representative image</div>}
          </>
        )}

        {dish.summary && <p className="body-serif clamp3 pt-12" style={{ margin: 0 }}>{dish.summary}</p>}

        <div className="pt-12">
          <span className="tag-box">{allergenLine(dish.allergens)}</span>
        </div>

        {reasons.length > 0 && (
          <div className="pt-16">
            {reasons.map((r) => (
              <div className="reason" key={r.label}>
                <div className="lab lab-sm reason-label">{r.label}</div>
                <div className="small">{r.text}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-auto">
        <div className="chip-row lab" style={{ borderTop: '1px solid var(--rule)' }}>
          {(refinements || []).map((r) => (
            <button key={r.value} className="chip lab" onClick={() => onRefine(r.value)} disabled={busy}>
              {r.label}
            </button>
          ))}
        </div>
        <div className="btn-pair">
          <button className="btn btn-line" onClick={onNext} disabled={busy}>
            <span className="lab">Next</span>
          </button>
          <button className="btn btn-accent" style={{ flex: 1.6 }} onClick={onChoose} disabled={busy}>
            <span className="lab">I'll have this</span>
          </button>
        </div>
      </div>
    </div>
  );
}
