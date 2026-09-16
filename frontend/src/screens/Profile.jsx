import { useEffect, useState } from 'react';
import * as api from '../api.js';
import { errorMessage, joinList, num, pct } from '../utils.js';

const DIMS = [
  ['sweet', 'Sweet'],
  ['salty', 'Salty'],
  ['sour', 'Sour'],
  ['bitter', 'Bitter'],
  ['umami', 'Savoury (umami)'],
  ['spice', 'Spice'],
];
const WEIGHTS = [
  ['w_health', 'Health'],
  ['w_budget', 'Budget'],
  ['w_taste', 'Taste'],
];
const KINDS = {
  approved: 'Chose',
  rejected: 'Passed on',
  refined: 'Asked for',
  query: 'Asked for',
};
const GOAL_NAMES = {
  balanced: 'Balanced',
  muscle_gain: 'Building muscle',
  weight_loss: 'Losing weight',
  light: 'Eating light',
};
const DIET_NAMES = { none: 'No restriction', vegetarian: 'Vegetarian', vegan: 'Vegan' };

/**
 * Everything the account holds: what approvals taught the model, the taste it
 * learned, what counts most, the rules, similar tastes, history and data rights.
 */
export default function Profile({ user, onClose, onSignedOut, toast }) {
  const [profile, setProfile] = useState(null);
  const [learned, setLearned] = useState(null);
  const [events, setEvents] = useState([]);
  const [similar, setSimilar] = useState(null);
  const [taste, setTaste] = useState({});
  const [weights, setWeights] = useState({});
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .profile()
      .then((p) => {
        setProfile(p);
        setTaste(p.taste?.vector || {});
        setWeights(p.taste?.agent_weights || { w_health: 0.34, w_budget: 0.33, w_taste: 0.33 });
      })
      .catch((err) => toast(errorMessage(err), 'error'));
    api.learning().then(setLearned).catch(() => {});
    api.history(8).then((r) => setEvents(r.events || [])).catch(() => {});
    api.similarTastes(3).then(setSimilar).catch(() => {});
  }, [toast]);

  const save = async (work, done) => {
    setBusy(true);
    try {
      const p = await work();
      setProfile(p);
      if (done) toast(done);
    } catch (err) {
      toast(errorMessage(err), 'error');
    } finally {
      setBusy(false);
    }
  };

  const commitTaste = (key, value) => {
    setTaste({ ...taste, [key]: value });
    save(() => api.setTaste({ [key]: value }));
  };

  const commitWeights = (key, value) => {
    const next = { ...weights, [key]: value };
    setWeights(next);
    save(() => api.setWeights(next));
  };

  const signOut = async () => {
    await api.logout().catch(() => {});
    onSignedOut();
  };

  const remove = () =>
    save(
      () => api.deleteAccount(password),
      null,
    ).then(() => {
      onSignedOut();
      toast('Your account and history are gone.');
    });

  const dietary = profile?.dietary;
  const goals = profile?.goals;

  return (
    <div className="screen">
      <div className="between pt-12">
        <div className="lab accent">Signed in</div>
        <button className="lab lab-sm muted" onClick={onClose}>
          Close ✕
        </button>
      </div>
      <div className="rule-thick draw" style={{ marginTop: 8 }} />

      <h2 className="h2 mask pt-16">{user?.display_name || 'Your table'}</h2>
      <div className="lab lab-sm muted pt-8">{user?.email}</div>

      {learned && (
        <div style={{ background: 'var(--ink)', color: 'var(--paper)', padding: 18, marginTop: 18 }}>
          <div className="lab lab-sm" style={{ color: 'var(--accent)' }}>What I've learned</div>
          {learned.summary?.map((line) => (
            <p key={line} className="body-serif" style={{ margin: '10px 0 0' }}>
              {line}
            </p>
          ))}
        </div>
      )}

      <div className="between pt-24">
        <div className="h3">Your taste</div>
        <button
          className="lab lab-sm accent"
          onClick={() => save(() => api.resetTaste(null), 'Back to your starting point.')}
          disabled={busy}
        >
          Reset
        </button>
      </div>
      <div className="pt-8">
        {DIMS.map(([key, label]) => (
          <div key={key} style={{ borderTop: '1px solid var(--rule)', padding: '10px 0' }}>
            <div className="between">
              <span className="lab lab-sm">{label}</span>
              <span className="bod-b" style={{ fontSize: 20 }}>{pct(taste[key])}</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={pct(taste[key])}
              onChange={(e) => setTaste({ ...taste, [key]: Number(e.target.value) / 100 })}
              onMouseUp={(e) => commitTaste(key, Number(e.target.value) / 100)}
              onTouchEnd={(e) => commitTaste(key, Number(e.target.value) / 100)}
              style={{ width: '100%', accentColor: 'var(--accent)' }}
            />
          </div>
        ))}
      </div>

      <div className="h3 pt-24">What counts most</div>
      <div className="pt-8">
        {WEIGHTS.map(([key, label]) => (
          <div key={key} style={{ borderTop: '1px solid var(--rule)', padding: '10px 0' }}>
            <div className="between">
              <span className="lab lab-sm">{label}</span>
              <span className="bod-b" style={{ fontSize: 20 }}>{pct(weights[key])}</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={pct(weights[key])}
              onChange={(e) => setWeights({ ...weights, [key]: Number(e.target.value) / 100 })}
              onMouseUp={(e) => commitWeights(key, Number(e.target.value) / 100)}
              onTouchEnd={(e) => commitWeights(key, Number(e.target.value) / 100)}
              style={{ width: '100%', accentColor: 'var(--accent)' }}
            />
          </div>
        ))}
        <div className="lab lab-sm muted pt-8">Your approvals keep adjusting these.</div>
      </div>

      <div className="h3 pt-24">Rules and goals</div>
      <div className="pt-8">
        {[
          ['Allergies', dietary?.allergies?.length ? joinList(dietary.allergies) : 'None'],
          ['Diet', DIET_NAMES[dietary?.diet] || dietary?.diet],
          ['Halal only', dietary?.halal_only ? 'On' : 'Off'],
          ['Eating for', GOAL_NAMES[goals?.goal] || goals?.goal],
          ['Usual spend', goals?.typical_spend_pkr ? `Rs ${goals.typical_spend_pkr}` : 'Not set'],
        ].map(([k, v]) => (
          <div key={k} className="between" style={{ borderTop: '1px solid var(--rule)', padding: '12px 0' }}>
            <span className="lab lab-sm muted">{k}</span>
            <span style={{ fontWeight: 600 }}>{v || '—'}</span>
          </div>
        ))}
      </div>

      {similar && (
        <>
          <div className="h3 pt-24">People with your taste</div>
          <div className="pt-8">
            {similar.matches?.map((m, i) => (
              <div key={i} className="between" style={{ padding: '6px 0' }}>
                <div className="bar" style={{ flex: 1, marginRight: 12 }}>
                  <span style={{ width: `${pct(m.similarity)}%` }} />
                </div>
                <span className="bod-b" style={{ fontSize: 18 }}>{pct(m.similarity)}</span>
              </div>
            ))}
            {similar.matches?.length > 0 && (
              <div className="lab lab-sm muted pt-8">No one is identified.</div>
            )}
            {similar.note && <div className="small muted">{similar.note}</div>}
          </div>
        </>
      )}

      {events.length > 0 && (
        <>
          <div className="h3 pt-24">Recently</div>
          <div className="pt-8">
            {events.map((e, i) => (
              <div key={e.event_id || i} style={{ borderTop: '1px solid var(--rule)', padding: '12px 0' }}>
                <div className="between">
                  <span className="lab lab-sm accent">{KINDS[e.kind] || e.kind}</span>
                  <span className="lab lab-sm muted">{num(i)}</span>
                </div>
                <div className="body-serif pt-8">{e.dish_name || e.query || '—'}</div>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="h3 pt-24">Your data</div>
      <div className="pt-8">
        <a className="between" href={api.exportUrl} style={{ borderTop: '1px solid var(--rule)', padding: '14px 0', textDecoration: 'none' }}>
          <span style={{ fontWeight: 600 }}>Download my data</span>
          <span className="bod">→</span>
        </a>
        <button className="between" onClick={signOut} style={{ width: '100%', borderTop: '1px solid var(--rule)', padding: '14px 0' }}>
          <span style={{ fontWeight: 600 }}>Sign out</span>
          <span className="bod">→</span>
        </button>
        <button
          className="between"
          onClick={() => setConfirming(true)}
          style={{ width: '100%', borderTop: '1px solid var(--rule)', padding: '14px 0', color: 'var(--accent)' }}
        >
          <span style={{ fontWeight: 600 }}>Delete account</span>
          <span className="bod">→</span>
        </button>
      </div>

      {confirming && (
        <div style={{ border: '2px solid var(--accent)', padding: 16, marginTop: 16 }}>
          <div className="small">
            This deletes your account, profile and history for good. Type your password to confirm.
          </div>
          <input
            className="field-box"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            style={{ marginTop: 10 }}
          />
          <div className="btn-pair" style={{ marginTop: 10 }}>
            <button className="btn btn-line" onClick={() => setConfirming(false)}>
              <span className="lab">Keep it</span>
            </button>
            <button className="btn btn-accent" onClick={remove} disabled={busy || !password}>
              <span className="lab">Delete for good</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
