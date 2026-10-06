import { useEffect, useState } from 'react';

/**
 * The dataset label: what the collection holds, how each part came to be known, and what the
 * build changed. The dish's own panel ("How we know this dish") accounts for one plate; this
 * accounts for the shelves, in the same badges and tones, so the two read as one claim.
 *
 * Everything on it is composed and counted by the server (GET /dataset → ui/dataset_label.py).
 * Nothing here is written into the page: if the count can't be taken, it says so.
 */
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
              Every dish here was read off a photograph of a real menu in Islamabad, checked by
              hand where a person could, and filled in by rule where the menu was silent — each
              step recorded against the dish it was done to. These are the counts, taken from the
              database this app is serving right now.
            </p>

            <div className="figures pt-16">
              {label.headline.map((h) => (
                <div className="figure" key={h.of}>
                  <div className="figure-num">{h.figure}</div>
                  <div className="lab lab-sm">{h.of}</div>
                  <div className="small muted">{h.note}</div>
                </div>
              ))}
            </div>

            <div className="h3 pt-24">What the build changed</div>
            <p className="small muted" style={{ margin: '4px 0 0' }}>
              The left column is what the data said when it arrived. The right is what the graph
              holds now, counted this minute.
            </p>
            <div className="changed pt-12">
              {label.changed.map((c) => (
                <div className="changed-row" key={c.what}>
                  <div className="lab lab-sm changed-what">{c.what}</div>
                  <div className="changed-pair">
                    <span className="badge is-unchecked">{c.before}</span>
                    <span className="changed-arrow">→</span>
                    <span className="badge is-confirmed">{c.after}</span>
                  </div>
                  <p className="small muted changed-note">{c.note}</p>
                </div>
              ))}
            </div>

            {label.sections.map((s) => (
              <div key={s.id} className="label-section">
                <div className="h3 pt-24">{s.title}</div>
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

            <div className="h3 pt-24">How the nutrition estimate was fitted</div>
            <p className="text" style={{ margin: '6px 0 0' }}>
              {label.calibration.matched}. The method we inherited ran{' '}
              {label.calibration.inherited}; the one in use runs {label.calibration.now}.{' '}
              {label.calibration.method}
            </p>
            <p className="small muted pt-8" style={{ margin: 0 }}>
              Median calories over the {label.nutrition.dishes.toLocaleString()} dishes the app can
              pick: {Math.round(label.nutrition.median_calories).toLocaleString()} kcal, a median{' '}
              {Math.round(100 * label.nutrition.median_fat_share)}% of energy from fat.{' '}
              {label.nutrition.over_three_quarters_fat} are estimated at over three quarters fat.
            </p>

            <button className="btn btn-line" style={{ marginTop: 24 }} onClick={onClose}>
              Close
            </button>
          </>
        )}
      </div>
    </>
  );
}
