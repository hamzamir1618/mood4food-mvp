import { useEffect, useState } from 'react';
import Glyph from '../components/icons.jsx';

/**
 * The dataset label: what the collection holds, how each part came to be known, and what the
 * build changed. The dish's own panel ("How we know this dish") accounts for one plate; this
 * accounts for the shelves, in the same badges and tones, so the two read as one claim.
 *
 * Everything on it is composed and counted by the server (GET /dataset → ui/dataset_label.py),
 * in words written for someone who never built it. Nothing here is a typed-in figure: if the
 * count can't be taken, it says so. The page only draws: the charts are the server's numbers.
 */

const pct = (share) => Math.round(100 * share);
const BETTER = {
  lower: '↓ lower is better',
  higher: '↑ higher is better',
  closer: 'closer to the lab is better',
};

/** "Before → now" for a share of calories: each a bar of the whole, the fat part filled. */
function ShareChart({ change }) {
  const rows = [
    ['Before', change.before_value, 'is-before'],
    ['Now', change.after_value, 'is-after'],
  ];
  const ref = change.reference;
  return (
    <div className="share-chart" role="img"
      aria-label={`Before ${pct(change.before_value)}%, now ${pct(change.after_value)}%${ref ? `; ${ref.label.toLowerCase()} ${pct(ref.value)}%` : ''}`}>
      {rows.map(([name, value, cls]) => (
        <div className="share-row" key={name}>
          <span className="lab lab-sm share-name">{name}</span>
          <span className="share-bar">
            <span className={`share-fill ${cls}`} style={{ width: `${pct(value)}%` }}>
              <span className="share-in">{pct(value)}% fat</span>
            </span>
            {ref && <span className="share-ref" style={{ left: `${pct(ref.value)}%` }} />}
          </span>
        </div>
      ))}
      {ref && (
        <div className="share-key small muted">
          <span className="share-key-line" aria-hidden="true" />
          {ref.label}: {pct(ref.value)}%
        </div>
      )}
    </div>
  );
}

/** "Before → now" for a count or an amount: two bars on one scale. */
function PairChart({ change }) {
  const top = Math.max(change.before_value || 0, change.after_value || 0) || 1;
  const rows = [
    ['Before', change.before_value, change.before, 'is-before'],
    ['Now', change.after_value, change.after, 'is-after'],
  ];
  return (
    <div className="pair-chart" role="img" aria-label={`Before ${change.before}, now ${change.after}`}>
      {rows.map(([name, value, shown, cls]) => (
        <div className="pair-row" key={name}>
          <span className="lab lab-sm share-name">{name}</span>
          <span className="pair-track">
            <span className={`pair-fill ${cls}`} style={{ width: `${Math.max(2, (100 * value) / top)}%` }} />
          </span>
          <span className={`bod-b pair-num ${cls}`}>{shown}</span>
        </div>
      ))}
    </div>
  );
}

/** A typical plate: how much of its calories are fat, as a ring around its calorie count. */
function Plate({ typical }) {
  const r = 38;
  const round = 2 * Math.PI * r;
  const fat = Math.max(0, Math.min(1, typical.fat_share));
  return (
    <div className="plate">
      <svg viewBox="0 0 100 100" className="plate-svg" role="img"
        aria-label={`A typical dish: about ${typical.calories} calories, ${pct(fat)}% from fat`}>
        <circle cx="50" cy="50" r={r} className="plate-rest" />
        <circle cx="50" cy="50" r={r} className="plate-fat"
          strokeDasharray={`${fat * round} ${round}`} transform="rotate(-90 50 50)" />
        <text x="50" y="49" textAnchor="middle" className="plate-num">{typical.calories}</text>
        <text x="50" y="61" textAnchor="middle" className="plate-unit">calories</text>
      </svg>
      <div>
        <div className="plate-key">
          <span className="key-swatch is-fat" /> <span className="small">From fat: about {pct(fat)}%</span>
        </div>
        <div className="plate-key">
          <span className="key-swatch is-rest" /> <span className="small">From carbohydrate and protein: the rest</span>
        </div>
        <p className="small muted" style={{ margin: '8px 0 0' }}>{typical.text}</p>
      </div>
    </div>
  );
}

/** How far each method was out against dishes measured in a laboratory. */
function ErrorChart({ calibration }) {
  const top = Math.max(calibration.error_before, calibration.error_now, 1) * 1.1;
  const rows = [
    ['The method we started with', calibration.error_before, 'is-before'],
    ['The method we use now', calibration.error_now, 'is-after'],
  ];
  return (
    <div className="pair-chart" role="img"
      aria-label={`Off by ${calibration.error_before} points before, ${calibration.error_now} now`}>
      {rows.map(([name, value, cls]) => (
        <div className="error-row" key={name}>
          <span className="small error-name">{name}</span>
          <span className="pair-track">
            <span className={`pair-fill ${cls}`} style={{ width: `${(100 * value) / top}%` }} />
          </span>
          <span className={`bod-b pair-num ${cls}`}>{Math.round(value)} points off</span>
        </div>
      ))}
    </div>
  );
}

export default function Label({ onClose }) {
  const [label, setLabel] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    fetch('/dataset')
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => live && setLabel(data))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, []);

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className="sheet sheet-tall" role="dialog" aria-label="How this dataset was built">
        <div className="between">
          <div className="lab accent">How this dataset was built</div>
          <button className="lab lab-sm muted" onClick={onClose}>
            Close ✕
          </button>
        </div>

        {failed && (
          <p className="text pt-16">
            The count couldn't be taken just now, and this page will not print a figure it hasn't
            counted. Try again in a moment.
          </p>
        )}
        {!label && !failed && <p className="lab lab-sm muted pt-16">Counting…</p>}

        {label && (
          <>
            <p className="body-serif pt-12" style={{ margin: 0 }}>
              Every dish in this app was read from a photo of a real menu in Islamabad. Where a
              person could, they checked it. Where the menu didn't say something, we filled it in
              by a rule and wrote down which rule. Every number on this page is counted from the
              data the app is using right now.
            </p>

            {label.legend?.length > 0 && (
              <div className="legend pt-16" aria-label="How to read the labels">
                <div className="lab lab-sm muted">How to read the labels</div>
                <div className="legend-grid">
                  {label.legend.map((l) => (
                    <div className="legend-item" key={l.tone}>
                      <span className={`badge is-${l.tone}`}>{l.badge}</span>
                      <span className="small">{l.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="figures pt-16">
              {label.headline.map((h) => (
                <div className="figure" key={h.of}>
                  <div className="figure-head">
                    <Glyph name={h.icon} size={22} />
                    <div className="figure-num">{h.figure}</div>
                  </div>
                  <div className="lab lab-sm">{h.of}</div>
                  <div className="small muted">{h.note}</div>
                </div>
              ))}
            </div>

            {label.typical && (
              <>
                <div className="h3 pt-24">A typical dish, in one picture</div>
                <Plate typical={label.typical} />
              </>
            )}

            <div className="h3 pt-24">What we fixed in the data</div>
            <p className="small muted" style={{ margin: '4px 0 0' }}>
              “Before” is what the data said when it reached us. “Now” is counted this minute.
            </p>
            <div className="changed pt-12">
              {label.changed.map((c) => (
                <div className="changed-card" key={c.what}>
                  <div className="changed-head">
                    <Glyph name={c.icon} size={22} />
                    <div className="lab changed-what">{c.title}</div>
                    {c.better && (
                      <span className="lab lab-sm muted changed-better">{BETTER[c.better]}</span>
                    )}
                  </div>
                  {c.kind === 'share' ? <ShareChart change={c} /> : <PairChart change={c} />}
                  <p className="small changed-note">{c.note}</p>
                </div>
              ))}
            </div>

            <div className="h3 pt-24">{label.calibration.title}</div>
            <p className="small" style={{ margin: '6px 0 0' }}>{label.calibration.plain}</p>
            <ErrorChart calibration={label.calibration} />
            <p className="small" style={{ margin: '8px 0 0' }}>{label.calibration.result}</p>
            <details className="why">
              <summary className="lab lab-sm">How we chose the method</summary>
              <p className="small muted" style={{ margin: '8px 0 0' }}>{label.calibration.how}</p>
              <p className="small muted" style={{ margin: '6px 0 0' }}>
                For the technically minded: {label.calibration.matched}; {label.calibration.method}
              </p>
            </details>

            {label.sections.map((s) => (
              <div key={s.id} className="label-section">
                <div className="section-head pt-24">
                  <Glyph name={s.icon} size={22} />
                  <div className="h3">{s.title}</div>
                </div>
                {s.note && (
                  <p className="small muted" style={{ margin: '4px 0 0' }}>
                    {s.note}
                  </p>
                )}
                <div className="pt-12">
                  {s.rows.map((r) => (
                    <div className="count-row" key={r.label}>
                      <div className="count-label small">{r.label}</div>
                      <div className="count-bar">
                        <span style={{ width: `${Math.max(r.share, 1)}%` }} />
                      </div>
                      <div className="bod-b count-num">{r.count.toLocaleString()}</div>
                      {r.badge ? (
                        <span className={`badge is-${r.tone}`}>{r.badge}</span>
                      ) : (
                        <span className="count-share lab lab-sm muted">{r.share}%</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}

            <button className="btn btn-line" style={{ marginTop: 24 }} onClick={onClose}>
              Close
            </button>
          </>
        )}
      </div>
    </>
  );
}
