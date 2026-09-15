import { useState } from 'react';

export default function RunnersUp({ candidates, winnerId }) {
  if (!candidates || !candidates.length) return null;
  const runners = candidates.filter(c => c.dish_id !== winnerId).slice(0, 4);
  if (!runners.length) return null;

  return (
    <div className="runners-up-section">
      <h3 className="runners-up-title">Other Top Matches</h3>
      <div className="runners-up-row">
        {runners.map(c => (
          <RunnerCard key={c.dish_id} candidate={c} />
        ))}
      </div>
    </div>
  );
}

function RunnerCard({ candidate }) {
  const [expanded, setExpanded] = useState(false);
  const c = candidate;
  const imgStyle = c.image_url ? { backgroundImage: `url('${c.image_url}')` } : {};
  // null means not assessed: an empty bar with a "Not assessed" hover, never a 0% score
  const pct = v => (v === null || v === undefined ? 0 : (v * 100).toFixed(0));
  const hint = v => (v === null || v === undefined ? 'Not assessed' : `${pct(v)}%`);
  const totalScore = pct(c.u_total);
  const health = pct(c.u_health);
  const budget = pct(c.u_budget);
  const taste = pct(c.u_taste);

  return (
    <div className={`runner-card ${expanded ? 'expanded' : ''}`} onClick={() => setExpanded(!expanded)}>
      <div className="runner-card-header">
        <div className="runner-img" style={imgStyle}>
          {c.is_rep_image && (
            <div style={{ position: 'absolute', bottom: 4, right: 4, background: 'rgba(0,0,0,0.6)', color: '#fff', padding: '2px 4px', borderRadius: 4, fontSize: 9 }}>
              Representative image
            </div>
          )}
        </div>
        <div className="runner-info">
          <div className="runner-name">{c.name}</div>
          {c.exploration && (
            <div className="runner-score" title={c.reasons?.exploration}>Something different</div>
          )}
          <div className="runner-score">⚡ {totalScore}% Match</div>
        </div>
        <button className="runner-expand-btn" aria-label="Expand breakdown" title="Click to view score breakdown">▼</button>
      </div>
      <div className="runner-breakdown">
        <div className="runner-bd-row" title={hint(c.u_health)}><span className="bd-label">💪 Health</span><div className="bd-bar-bg"><div className="bd-bar-fill health" style={{ width: `${health}%` }}></div></div></div>
        <div className="runner-bd-row" title={hint(c.u_budget)}><span className="bd-label">💰 Budget</span><div className="bd-bar-bg"><div className="bd-bar-fill budget" style={{ width: `${budget}%` }}></div></div></div>
        <div className="runner-bd-row" title={hint(c.u_taste)}><span className="bd-label">😋 Taste</span><div className="bd-bar-bg"><div className="bd-bar-fill taste" style={{ width: `${taste}%` }}></div></div></div>
      </div>
    </div>
  );
}
