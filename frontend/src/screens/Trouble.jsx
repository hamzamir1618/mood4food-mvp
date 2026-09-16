/**
 * The two ways a request can end without a dish: nothing fitted, or the server
 * couldn't be reached. Neither ever offers to relax an allergy or a diet.
 */
export default function Trouble({ kind, message, onRetry, onRestart, onWiden }) {
  const offline = kind === 'offline';

  return (
    <div className="screen">
      <div className="lab accent rise pt-16">{offline ? 'No connection' : 'Nothing fits'}</div>
      <div className="rule-thick draw" style={{ marginTop: 8 }} />

      <h2 className="h2 mask pt-16">
        {offline ? "Can't reach Mood4Food right now." : 'Nothing fits yet.'}
      </h2>

      <p className="body-serif rise pt-12" style={{ margin: 0 }}>
        {offline
          ? 'Check your connection and try again. What you asked for is still here.'
          : 'No dish meets this request and your rules together. Your allergies and diet stay exactly as they are.'}
      </p>

      {message && !offline && <div className="small muted pt-12">{message}</div>}

      <div className="mt-auto pt-24" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {offline ? (
          <button className="btn btn-accent btn-wide" onClick={onRetry}>
            <span className="lab">Try again</span>
            <span className="bod" style={{ fontSize: 20 }}>→</span>
          </button>
        ) : (
          <>
            {onWiden && (
              <button className="btn btn-line btn-wide" onClick={onWiden}>
                <span className="lab">Let me spend a bit more</span>
                <span className="bod" style={{ fontSize: 20 }}>→</span>
              </button>
            )}
            <button className="btn btn-accent btn-wide" onClick={onRestart}>
              <span className="lab">Ask for something else</span>
              <span className="bod" style={{ fontSize: 20 }}>→</span>
            </button>
          </>
        )}
        <button className="btn btn-text" onClick={onRestart}>
          <span className="lab lab-sm">Start over</span>
        </button>
      </div>
    </div>
  );
}
