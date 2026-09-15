import { extractWinnerReasons } from '../utils.js';

export default function WinnerCard({ dish, scores, traces, onAlternate, alternateDisabled, alternateText }) {
  if (!dish || !dish.dish_id) return null;

  const name = dish.name || 'No dish selected';
  const price = dish.price_pkr ?? '—';
  const pct = ((scores.u_total ?? 0) * 100).toFixed(0);
  const imgUrl = dish.image_url || '';
  const bgStyle = imgUrl
    ? { backgroundImage: `linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.15) 50%, transparent 100%), url('${imgUrl}')` }
    : {};

  const agentReasons = extractWinnerReasons(dish.name || '', traces || []);
  const agentIcons = { 'Health Agent': '💪', 'Budget Agent': '💰', 'Taste Agent': '😋' };

  return (
    <div className="winner-card" id="winner-card" style={bgStyle}>
      <div className="winner-card-content">
        {dish.is_rep_image && (
          <div className="rep-img-label" style={{ position: 'absolute', top: 12, right: 12, background: 'rgba(0,0,0,0.6)', color: '#fff', padding: '4px 8px', borderRadius: 4, fontSize: 11 }}>
            Representative image
          </div>
        )}
        <div className="winner-label">🏆 Best Pick For You</div>
        <div className="winner-dish-name" id="winner-name">{name}</div>
        <div id="winner-reasons-container">
          {agentReasons.length > 0 ? (
            <div className="winner-reasons">
              <div className="reasons-title">🤔 Why this?</div>
              {agentReasons.map((r, i) => {
                const icon = agentIcons[r.agent] || '🤖';
                return (
                  <div key={i} className="reason-line">
                    <span className="reason-icon">{icon}</span> <strong>{r.agent}:</strong> {r.reason}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="winner-tags" id="winner-tags">
              {(dish.human_tags || []).map((t, i) => (
                <span key={i} className="tag-pill">{t}</span>
              ))}
            </div>
          )}
        </div>
        <div className="winner-meta">
          <span className="winner-meta-item" id="winner-price">🏷️ Rs. {price}</span>
          <span className="winner-meta-item winner-category" id="winner-category">{dish.category || ''}</span>
        </div>
        <div className="winner-score-badge" id="winner-score">⚡ {pct}% Match</div>
        <button
          id="btn-alternate"
          className="btn-alternate"
          onClick={onAlternate}
          disabled={alternateDisabled}
        >
          {alternateText || 'Not quite — show me something else'}
        </button>
      </div>
    </div>
  );
}
