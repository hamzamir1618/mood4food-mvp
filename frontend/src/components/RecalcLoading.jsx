export default function RecalcLoading({ visible }) {
  if (!visible) return null;
  return (
    <div id="recalc-loading" className="recalc-loading" style={{ display: 'flex' }}>
      <div className="spinner"></div> Recalculating...
    </div>
  );
}
