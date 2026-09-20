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

/** How a request runs, shown along the foot of the wide layout. */
const STEPS = [
  ['Say what you feel like', 'A mood, a craving, a budget, in your own words.'],
  ['Answer two questions', 'At most two, and only when they would change the pick.'],
  ['Get one dish, with reasons', 'From a real Islamabad menu, weighed for taste, budget, health and distance.'],
];

/** A slowly turning stamp beside the headline on wide screens. Decorative only. */
function Stamp() {
  return (
    <svg className="stamp" viewBox="0 0 200 200" aria-hidden="true">
      <defs>
        <path id="stamp-circle" d="M100,100 m-78,0 a78,78 0 1,1 156,0 a78,78 0 1,1 -156,0" />
      </defs>
      <circle cx="100" cy="100" r="96" className="stamp-ring" />
      <circle cx="100" cy="100" r="60" className="stamp-ring thin" />
      <g className="stamp-spin">
        <text className="stamp-text">
          <textPath href="#stamp-circle">REAL MENUS · REAL PRICES · ISLAMABAD ·</textPath>
        </text>
      </g>
      <text x="100" y="124" textAnchor="middle" className="stamp-core">
        4
      </text>
    </svg>
  );
}

export default function Home({ onStart, busy, initialQuery, onAbout }) {
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
    <div className="screen home">
      <div className="home-title">
        <h1 className="h1 mask pt-16">
          What are
          <br />
          you in the
          <br />
          <span style={{ fontStyle: 'italic' }}>mood</span> for?
        </h1>
        <Stamp />
      </div>

      <p className="home-tagline body-serif rise" style={{ animationDelay: '120ms' }}>
        One dish from real Islamabad menus, with the reasons shown.
      </p>

      <div className="home-moods">
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
      </div>

      <div className="home-query rise pt-24" style={{ animationDelay: '420ms' }}>
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
          maxLength={500}
          style={{ marginTop: 6 }}
        />
      </div>

      <div className="home-cta mt-auto pt-24">
        <button className="btn btn-ink btn-wide rise" onClick={start} disabled={busy || !query.trim()}>
          <span className="lab">{busy ? 'Finding it' : 'Ask me two questions'}</span>
          {busy ? (
            <span className="spinner" />
          ) : (
            <span className="bod btn-arrow" style={{ fontSize: 22 }}>
              →
            </span>
          )}
        </button>
      </div>

      <ol className="home-steps wide-only stagger" aria-label="How it works">
        {STEPS.map(([title, text], i) => (
          <li key={title}>
            <span className="home-step-num">{num(i)}</span>
            <span className="home-step-title">{title}</span>
            <span className="small muted">{text}</span>
          </li>
        ))}
      </ol>

      <div className="home-foot">
        <div className="ticker" style={{ marginTop: 18 }}>
          <div className="ticker-track lab lab-sm muted">
            <span>{TICKER}</span>
            <span>{TICKER}</span>
            <span>{TICKER}</span>
            <span>{TICKER}</span>
          </div>
        </div>
        <button className="lab lab-sm muted" onClick={onAbout} style={{ padding: '10px 0 0' }}>
          Nutrition estimated · distances © OpenStreetMap · where the data comes from →
        </button>
      </div>
    </div>
  );
}
