export default function RelaxationNotice({ notice }) {
  if (!notice) return null;
  return (
    <div className="relaxation-notice">
      <div className="relaxation-icon">⚠️</div>
      <div className="relaxation-text">{notice}</div>
    </div>
  );
}
