import { escapeHtml } from '../utils.js';

export default function EmptyState({ recents, onRecentClick }) {
  return (
    <div
      className="empty-state"
      id="empty-state"
      style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '3rem', color: 'var(--text-color)' }}
    >
      <div className="empty-icon" style={{ fontSize: '3rem', marginBottom: '1rem' }}>👋</div>
      <h3>Tell me what you're craving, or how much you want to spend — I'll find the best match</h3>
      {recents && recents.length > 0 && (
        <div id="recent-searches-container" style={{ marginTop: '2rem' }}>
          <h4 style={{ marginBottom: '1rem', opacity: 0.7 }}>Recent Searches</h4>
          <div id="recent-searches-list" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
            {recents.map((text, i) => (
              <button
                key={i}
                className="recent-search-btn"
                style={{
                  background: 'var(--surface-light)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-color)',
                  padding: '0.5rem 1rem',
                  borderRadius: '9999px',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  fontSize: '0.875rem',
                  transition: 'background 0.2s',
                }}
                onClick={() => onRecentClick(text)}
              >
                {text}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
