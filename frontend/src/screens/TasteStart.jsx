import { useEffect, useState } from 'react';

/**
 * Taste in fifteen seconds: six dishes, tap the ones you'd eat.
 *
 * Before this, a first-time reader's flavour term sat out entirely — the card said "No flavour
 * to go on yet" and the taste slider did nothing. Six taps are enough to switch it on honestly.
 * The server chooses the six and reads the taps (accounts/taste_start.py); this screen only
 * collects them, and says back what was understood, in the app's own words, before closing.
 *
 * The photographs are stock images of the kind of dish, which the card says outright: no dish
 * in the collection has a photograph of its own, and a picture presented as the plate would be
 * the one dishonest thing on a screen whose whole point is what we actually know.
 */
export default function TasteStart({ onClose, onDone }) {
  const [dishes, setDishes] = useState(null);
  const [least, setLeast] = useState(2);
  const [chosen, setChosen] = useState([]);
  const [said, setSaid] = useState(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    fetch('/taste/start')
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => {
        if (!live) return;
        setDishes(data.dishes);
        setLeast(data.least);
      })
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, []);

  const toggle = (id) =>
    setChosen((was) => (was.includes(id) ? was.filter((x) => x !== id) : [...was, id]));

  const send = async () => {
    setBusy(true);
    try {
      const reply = await fetch('/taste/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dish_ids: chosen }),
      });
      if (!reply.ok) throw new Error(reply.status);
      const data = await reply.json();
      setSaid(data.said);
      onDone?.(data);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className="sheet sheet-tall" role="dialog" aria-label="What you like">
        <div className="between">
          <div className="lab accent">What do you like?</div>
          <button className="lab lab-sm muted" onClick={onClose}>
            {said ? 'Close ✕' : 'Skip ✕'}
          </button>
        </div>

        {failed && (
          <p className="text pt-16">
            That didn't go through. You can keep going without it — the app will learn your taste
            from what you approve instead.
          </p>
        )}

        {said ? (
          <>
            <p className="body-serif pt-16" style={{ margin: 0 }}>
              {said}
            </p>
            <p className="small muted pt-12" style={{ margin: 0 }}>
              Your taste now counts in every pick, and you can see and change it any time under
              your account. Nothing here is fixed: what you approve moves it further than this did.
            </p>
            <button className="btn btn-ink" style={{ marginTop: 20 }} onClick={onClose}>
              <span className="lab">Good</span>
            </button>
          </>
        ) : (
          <>
            <p className="body-serif pt-12" style={{ margin: 0 }}>
              Tap the ones you'd actually eat — at least {least}. It takes about fifteen seconds,
              and it's the difference between a pick weighed for your taste and one that has to
              leave taste out.
            </p>

            {!dishes && !failed && <p className="lab lab-sm muted pt-16">Finding six dishes…</p>}

            <div className="taste-grid pt-16">
              {(dishes || []).map((d) => {
                const on = chosen.includes(d.dish_id);
                return (
                  <button
                    key={d.dish_id}
                    className={`taste-card${on ? ' is-on' : ''}`}
                    onClick={() => toggle(d.dish_id)}
                    aria-pressed={on}
                  >
                    <div className="photo taste-photo">
                      <img src={d.image_url} alt="" draggable="false" />
                      <span className="taste-tick lab lab-sm">{on ? '✓' : ''}</span>
                    </div>
                    <div className="lab lab-sm taste-name">{d.name}</div>
                    <div className="small muted">
                      {d.restaurant_name}
                      {d.restaurant_area ? ` · ${d.restaurant_area}` : ''}
                    </div>
                    <div className="small muted">Representative image</div>
                  </button>
                );
              })}
            </div>

            <button
              className="btn btn-ink"
              style={{ marginTop: 20 }}
              disabled={busy || chosen.length < least}
              onClick={send}
            >
              <span className="lab">
                {busy
                  ? 'Saving'
                  : chosen.length < least
                    ? `Tap ${least - chosen.length} more`
                    : `Use these ${chosen.length}`}
              </span>
            </button>
          </>
        )}
      </div>
    </>
  );
}
