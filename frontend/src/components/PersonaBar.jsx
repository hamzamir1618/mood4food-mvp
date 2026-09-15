export default function PersonaBar({ personas, currentPersona, onSelect }) {
  if (!personas || !Object.keys(personas).length) return null;

  return (
    <div className="persona-bar">
      <div className="persona-scroll">
        {Object.entries(personas).map(([key, p]) => (
          <button
            key={key}
            className={`persona-chip ${key === currentPersona ? 'active' : ''}`}
            data-persona={key}
            aria-label={`Persona: ${p.display_name}`}
            aria-pressed={key === currentPersona}
            onClick={() => onSelect(key)}
          >
            <span className="persona-icon">{p.icon}</span>
            <span className="persona-name">{p.display_name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
