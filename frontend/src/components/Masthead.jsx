const today = () =>
  new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

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
