export default function XaiSection({ traces, open, onToggle }) {
  if (!traces || !traces.length) return null;

  return (
    <div className="xai-section">
      <button className="xai-toggle" id="xai-toggle" onClick={onToggle}>
        <span className="xai-toggle-left"><span>⚙️</span> Developer Mode — AI Reasoning Trace</span>
        <span className={`xai-chevron ${open ? 'open' : ''}`} id="xai-chevron">▼</span>
      </button>
      <div className={`xai-panel ${open ? 'open' : ''}`} id="xai-panel">
        <div className="xai-panel-inner" id="xai-inner">
          {traces.map((t, i) => {
            const isWinner = t.startsWith('winner:');
            return (
              <div key={i} className={`xai-trace-line ${isWinner ? 'winner-line' : ''}`}>{t}</div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
