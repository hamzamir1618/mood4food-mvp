import { useEffect, useRef, useState } from 'react';
import { matchOf, scoreRows } from '../utils.js';
import { Slot, layoutOf } from '../components/blocks.jsx';

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

/**
 * The pick. What the card shows is the server's decision: it sends a layout — which blocks, in
 * which column, in what order, drawn how — and this screen draws it (docs/SERVER_DRIVEN_UI.md).
 * Without a layout it draws the fixed one, which is the screen this always was.
 */
export default function Pick({
  blueprint,
  refinements,
  onRefine,
  onNext,
  onChoose,
  onScores,
  onWeights,
  onDataset,
  busy,
  rank,
}) {
  const dish = blueprint?.winning_dish || {};
  const match = matchOf(blueprint);
  const shown = useCountUp(match);
  const [dx, setDx] = useState(0);
  const [imageFailed, setImageFailed] = useState(false);
  const drag = useRef({ on: false, x: 0, moved: false });
  const hasPhoto = Boolean(dish.image_url) && !imageFailed;

  const layout = layoutOf(blueprint);
  const ctx = {
    blueprint,
    dish,
    shown,
    reasons: scoreRows(blueprint),
    hasPhoto,
    onImageError: () => setImageFailed(true),
    onScores,
    onWeights,
    onDataset,
    busy,
  };
  // The layout's own account of itself, shown only if the reader opens it.
  const why = (layout.why || []).filter((w) => w.text);
  // The server decides which refinement is worth offering first.
  const order = layout.actions?.refinements;
  const chips = order
    ? [...(refinements || [])].sort((a, b) => order.indexOf(a.value) - order.indexOf(b.value))
    : refinements || [];

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
    <div className="screen pick">
      <div className="pick-bar">
        <div className="between pt-12">
          <div className="lab accent">The pick · {rank}</div>
          <div className="lab lab-sm muted">
            <span className="touch-only">Swipe for the next dish</span>
            <span className="wide-only">Drag the card, or choose below</span>
          </div>
        </div>
        <div className="rule-thick draw" style={{ marginTop: 8 }} />
        {/* Said out loud when the search had to widen, so a substitute never reads as a match. */}
        {blueprint?.relaxation_notice && (
          <p className="pick-notice small rise" role="status">
            {blueprint.relaxation_notice}
          </p>
        )}
      </div>

      <div
        className={`pick-card${hasPhoto ? '' : ' no-photo'}`}
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
        <div className="pick-main">
          <Slot layout={layout} slot="main" ctx={ctx} />
        </div>

        <div className="pick-side">
          <Slot layout={layout} slot="side" ctx={ctx} />
        </div>

        <div className="pick-runners o-13" data-nodrag="1">
          <Slot layout={layout} slot="band" ctx={ctx} />
          {why.length > 0 && (
            <details className="why why-layout" data-nodrag="1">
              <summary className="lab lab-sm">Why the page looks like this</summary>
              <ul className="why-lines small">
                {why.map((w) => (
                  <li key={w.text}>{w.text}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      </div>

      <div className="pick-actions mt-auto">
        <div className="chip-row lab" style={{ borderTop: '1px solid var(--rule)' }}>
          {chips.map((r) => (
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
