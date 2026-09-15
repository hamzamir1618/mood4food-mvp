import CornerFlourish from './CornerFlourish.jsx';

/**
 * CardFrame — ornamental frame wrapper that places CornerFlourish
 * elements at each corner of its children. Also applies the
 * linen-texture background and gold border styling.
 *
 * @param {React.ReactNode} children
 * @param {string}  className  — extra CSS classes on the outer wrapper
 * @param {boolean} showCorners — show corner flourishes (default true)
 * @param {number}  cornerSize — flourish size in px (default 32)
 * @param {string}  accentColor — CSS color for flourishes (default 'var(--gold-muted)')
 */
export default function CardFrame({
  children,
  className = '',
  showCorners = true,
  cornerSize = 32,
  accentColor = 'var(--gold-muted)',
}) {
  return (
    <div
      className={`ornament-card-frame ${className}`}
      style={{ color: accentColor }}
    >
      {showCorners && (
        <>
          <CornerFlourish size={cornerSize} position="tl" className="ornament-card-frame__corner ornament-card-frame__corner--tl" />
          <CornerFlourish size={cornerSize} position="tr" className="ornament-card-frame__corner ornament-card-frame__corner--tr" />
          <CornerFlourish size={cornerSize} position="bl" className="ornament-card-frame__corner ornament-card-frame__corner--bl" />
          <CornerFlourish size={cornerSize} position="br" className="ornament-card-frame__corner ornament-card-frame__corner--br" />
        </>
      )}
      <div className="ornament-card-frame__content">
        {children}
      </div>
    </div>
  );
}
