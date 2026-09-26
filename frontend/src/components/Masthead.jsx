import { useState } from 'react';
import { currentTheme, setTheme } from '../theme.js';

const today = () =>
  new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

/** Light or dark. The system decides until the reader does; then their choice is remembered. */
function ThemeToggle() {
  const [theme, set] = useState(currentTheme);
  const next = theme === 'dark' ? 'light' : 'dark';
  return (
    <button
      className="lab lab-sm theme-toggle"
      onClick={() => set(setTheme(next))}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
    >
      {theme === 'dark' ? '☀ Light' : '☾ Dark'}
    </button>
  );
}

/** The masthead: a rule, the wordmark between two small labels, another rule. Wide screens add a dateline. */
export default function Masthead({ left, right, onBack, onProfile }) {
  return (
    <div className="masthead">
      <div className="rule-thick draw" />
      <div className="masthead-row">
        <div className="masthead-side">
          {onBack ? (
            <button className="lab lab-sm" onClick={onBack}>
              ← Back
            </button>
          ) : (
            <div className="lab lab-sm">{left}</div>
          )}
        </div>
        <div className="masthead-word">Mood4Food</div>
        <div className="masthead-side right">
          <ThemeToggle />
          {onProfile ? (
            <button className="lab lab-sm accent" onClick={onProfile}>
              {right}
            </button>
          ) : (
            <div className="lab lab-sm accent">{right}</div>
          )}
        </div>
      </div>
      <div className="rule-ink draw" style={{ animationDelay: '120ms' }} />
      <div className="masthead-dateline wide-only lab lab-sm muted">
        <span>{today()}</span>
        <span>Islamabad · real menus, real prices</span>
      </div>
    </div>
  );
}
