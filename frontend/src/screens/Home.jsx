import { useState } from 'react';
import { num } from '../utils.js';

/** The moods are shorthand for a typed request; the backend reads them as text. */
const MOODS = [
  { text: 'something spicy for dinner', label: 'Something spicy' },
  { text: 'something sweet', label: 'Something sweet' },
  { text: 'cheap eats', label: 'Cheap eats' },
  { text: 'light and healthy', label: 'Light & healthy' },
];

const TICKER = 'Real menus · real prices · allergens in full · nothing sponsored · ';

export default function Home({ onStart, busy, initialQuery }) {
  const [picked, setPicked] = useState(initialQuery ? -1 : 0);
  const [query, setQuery] = useState(initialQuery || MOODS[0].text);

  const choose = (i) => {
    setPicked(i);
    setQuery(MOODS[i].text);
  };

  const start = () => {
    const text = query.trim();
    if (text && !busy) onStart(text);
  };

  return (
    <div className="screen">
      <h1 className="h1 mask pt-16">
        What are
        <br />
        you in the
        <br />
        <span style={{ fontStyle: 'italic' }}>mood</span> for?
      </h1>

      <div className="lab rise muted pt-16" style={{ animationDelay: '200ms' }}>
        Pick one, or write your own
      </div>

      <div className="stagger pt-12">
        {MOODS.map((mood, i) => (
          <div key={mood.label} style={{ borderTop: '1px solid var(--rule)' }}>
            <button
              className={`row${picked === i ? ' is-on' : ''}`}
              onClick={() => choose(i)}
              aria-pressed={picked === i}
            >
              <span className="row-fill" />
              <span className="row-num">{num(i)}</span>
              <span className="row-label">{mood.label}</span>
              <span className="row-mark lab lab-sm">{picked === i ? 'Chosen' : ''}</span>
            </button>
          </div>
        ))}
        <div style={{ borderTop: '1px solid var(--rule)' }} />
      </div>

      <div className="rise pt-24" style={{ animationDelay: '420ms' }}>
        <label className="lab lab-sm muted" htmlFor="query">
          In your own words
        </label>
        <input
          id="query"
          className="field"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPicked(-1);
          }}
          onKeyDown={(e) => e.key === 'Enter' && start()}
          placeholder="Tell me what you'd like to eat"
          style={{ marginTop: 6 }}
        />
      </div>

      <div className="mt-auto pt-24">
        <button className="btn btn-ink btn-wide rise" onClick={start} disabled={busy}>
          <span className="lab">{busy ? 'Finding it' : 'Ask me two questions'}</span>
          {busy ? <span className="spinner" /> : <span className="bod" style={{ fontSize: 22 }}>→</span>}
        </button>
        <div className="ticker" style={{ marginTop: 18 }}>
          <div className="ticker-track lab lab-sm muted">
            <span>{TICKER}</span>
            <span>{TICKER}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
