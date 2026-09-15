/**
 * SectionDivider — ornamental horizontal rule with central motif.
 *
 * Three variants:
 *  'diamond'  — thin rules flanking a central diamond (default)
 *  'flourish' — thin rules flanking a small scroll ornament
 *  'simple'   — thin rule with small central dot
 *
 * Uses currentColor. Typical parent color: var(--gold) or var(--gold-muted).
 *
 * @param {'diamond'|'flourish'|'simple'} variant
 * @param {string} className
 */
export default function SectionDivider({ variant = 'diamond', className = '' }) {
  return (
    <div
      className={`ornament-divider ornament-divider--${variant} ${className}`}
      role="separator"
      aria-hidden="true"
    >
      {variant === 'diamond' && <DiamondDivider />}
      {variant === 'flourish' && <FlourishDivider />}
      {variant === 'simple' && <SimpleDivider />}
    </div>
  );
}

function DiamondDivider() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 400 20"
      preserveAspectRatio="none"
      fill="currentColor"
      stroke="currentColor"
      className="ornament-divider__svg"
      aria-hidden="true"
    >
      {/* Left rule */}
      <line x1="0" y1="10" x2="170" y2="10" strokeWidth="0.75" opacity="0.35" />
      {/* Left inner dot */}
      <circle cx="175" cy="10" r="1.5" opacity="0.4" stroke="none" />
      {/* Central diamond */}
      <path d="M192,4 L200,10 L192,16 L184,10Z" strokeWidth="1" fill="none" opacity="0.6" />
      {/* Inner diamond (smaller) */}
      <path d="M195,7 L200,10 L195,13 L190,10Z" fill="currentColor" stroke="none" opacity="0.3" />
      {/* Right inner dot */}
      <circle cx="225" cy="10" r="1.5" opacity="0.4" stroke="none" />
      {/* Right rule */}
      <line x1="230" y1="10" x2="400" y2="10" strokeWidth="0.75" opacity="0.35" />
    </svg>
  );
}

function FlourishDivider() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 400 24"
      preserveAspectRatio="none"
      fill="currentColor"
      stroke="currentColor"
      className="ornament-divider__svg"
      aria-hidden="true"
    >
      {/* Left rule */}
      <line x1="0" y1="12" x2="155" y2="12" strokeWidth="0.75" opacity="0.35" />
      {/* Left scroll */}
      <path
        d="M160,12 C164,6 172,4 178,8 C182,10 180,14 176,14"
        fill="none" strokeWidth="1" opacity="0.5" strokeLinecap="round"
      />
      {/* Center dot */}
      <circle cx="200" cy="12" r="2.5" opacity="0.5" stroke="none" />
      {/* Right scroll (mirrored) */}
      <path
        d="M240,12 C236,6 228,4 222,8 C218,10 220,14 224,14"
        fill="none" strokeWidth="1" opacity="0.5" strokeLinecap="round"
      />
      {/* Right rule */}
      <line x1="245" y1="12" x2="400" y2="12" strokeWidth="0.75" opacity="0.35" />
    </svg>
  );
}

function SimpleDivider() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 400 10"
      preserveAspectRatio="none"
      fill="currentColor"
      stroke="currentColor"
      className="ornament-divider__svg"
      aria-hidden="true"
    >
      {/* Left rule */}
      <line x1="20" y1="5" x2="193" y2="5" strokeWidth="0.5" opacity="0.25" />
      {/* Center dot */}
      <circle cx="200" cy="5" r="2" opacity="0.4" stroke="none" />
      {/* Right rule */}
      <line x1="207" y1="5" x2="380" y2="5" strokeWidth="0.5" opacity="0.25" />
    </svg>
  );
}
