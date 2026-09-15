/**
 * CornerFlourish — calligraphic scroll bracket for card corners.
 *
 * Renders in one orientation (top-left); use CSS transform to
 * rotate/flip for other corners. Uses currentColor → inherits
 * from parent (typically gold-muted or gold).
 *
 * @param {number}  size      — bounding box in px (default 36)
 * @param {string}  className — optional extra CSS class
 * @param {string}  position  — 'tl' | 'tr' | 'bl' | 'br' (default 'tl')
 */
export default function CornerFlourish({ size = 36, className = '', position = 'tl' }) {
  const transforms = {
    tl: '',
    tr: 'scaleX(-1)',
    bl: 'scaleY(-1)',
    br: 'scale(-1)',
  };

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 60 60"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      className={`ornament-corner ${className}`}
      style={{ transform: transforms[position] || '' }}
      aria-hidden="true"
    >
      {/* Main bracket arm — vertical */}
      <path
        d="M8,2 L8,32"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      {/* Main bracket arm — horizontal */}
      <path
        d="M8,8 L38,8"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      {/* Inner scroll curl — flows from vertical arm inward */}
      <path
        d="M8,32 C8,40 14,44 20,42 C26,40 28,34 24,30 C20,26 14,28 14,34"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      {/* Outer horizontal terminus — small curl at the end */}
      <path
        d="M38,8 C44,8 48,12 46,16 C44,20 40,20 40,16"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      {/* Corner dot */}
      <circle cx="8" cy="8" r="2" fill="currentColor" stroke="none" />
    </svg>
  );
}
