import { healthLabel, budgetLabel, tasteLabel, parseReasons } from '../utils.js';

export default function ScoresCard({ scores, traces, dish }) {
  const reasons = parseReasons(traces, dish?.name);
  const items = [
    { label: 'Healthy', key: 'u_health', cls: 'health', labelFn: healthLabel, reason: reasons.health },
    { label: 'Affordable', key: 'u_budget', cls: 'budget', labelFn: budgetLabel, reason: reasons.budget },
    { label: 'Tasty', key: 'u_taste', cls: 'taste', labelFn: tasteLabel, reason: reasons.taste },
  ];

  return (
    <div className="scores-card">
      <h2><span>📊</span> How It Scores</h2>
      {items.map(item => {
        // null means the dish couldn't be assessed on this: show that, not a 0% score
        const known = scores[item.key] !== null && scores[item.key] !== undefined;
        const val = known ? scores[item.key] : 0;
        const pct = known ? `${(val * 100).toFixed(0)}%` : '—';
        const lab = known ? item.labelFn(val) : 'Not assessed';
        return (
          <div key={item.cls} className="score-row-wrapper">
            <div className="score-row">
              <div className="score-label">
                <div className={`score-dot ${item.cls}`}></div>
                <span className={`score-label-text ${item.cls}`}>{lab}</span>
              </div>
              <div className="score-bar-container">
                <div className={`score-bar-fill ${item.cls}`} style={{ width: `${Math.min(val * 100, 100)}%` }}></div>
              </div>
              <div className={`score-value ${item.cls}`}>{pct}</div>
            </div>
            {item.reason && <div className={`score-reason ${item.cls}`}>↳ {item.reason}</div>}
          </div>
        );
      })}
    </div>
  );
}
