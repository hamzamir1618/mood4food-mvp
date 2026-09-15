export default function ErrorState({ message, onRetry }) {
  return (
    <div className="error-state" id="error-state" style={{ display: 'flex' }}>
      <div className="error-icon">😔</div>
      <h3>Couldn't load recommendations</h3>
      <p id="error-message">{message || 'Make sure the backend server is running on port 8000.'}</p>
      <button onClick={onRetry}>Try Again</button>
    </div>
  );
}
