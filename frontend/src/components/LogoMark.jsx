import { useId } from 'react';

/**
 * Mood4Food emblem mark — wax-seal compass with fork-tines north point.
 * Uses currentColor (inherits from parent CSS `color`).
 *
 * @param {number} size — width/height in px (default 40)
 * @param {string} className — optional CSS class
 */
export default function LogoMark({ size = 40, className = '' }) {
  const uid = useId();
  const maskId = `m4f-mark${uid}`;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 200 200"
      fill="currentColor"
      width={size}
      height={size}
      className={className}
      role="img"
      aria-label="Mood4Food"
    >
      <defs>
        <mask id={maskId}>
          <rect width="200" height="200" fill="white" />
          <circle cx="100" cy="100" r="14" fill="black" />
        </mask>
      </defs>

      {/* Outer seal ring */}
      <circle cx="100" cy="100" r="90" fill="none" stroke="currentColor" strokeWidth="4" />
      {/* Inner decorative ring */}
      <circle cx="100" cy="100" r="76" fill="none" stroke="currentColor" strokeWidth="1.5" />

      {/* Seal studs — cardinal */}
      <circle cx="100" cy="7" r="6" />
      <circle cx="193" cy="100" r="6" />
      <circle cx="100" cy="193" r="6" />
      <circle cx="7" cy="100" r="6" />
      {/* Seal studs — intercardinal */}
      <circle cx="165.8" cy="34.2" r="4" />
      <circle cx="165.8" cy="165.8" r="4" />
      <circle cx="34.2" cy="165.8" r="4" />
      <circle cx="34.2" cy="34.2" r="4" />

      {/* Compass rose with center void */}
      <g mask={`url(#${maskId})`}>
        {/* Main star (E-S-W points) */}
        <path d="M107,93 L166,100 L107,107 L100,166 L93,107 L34,100 L93,93Z" />
        {/* North: fork tines */}
        <rect x="93" y="38" width="4.5" height="62" rx="2.25" />
        <rect x="97.75" y="28" width="4.5" height="72" rx="2.25" />
        <rect x="102.5" y="38" width="4.5" height="62" rx="2.25" />
        {/* Secondary star (45° rotation) */}
        <path d="M125,75 L114,100 L125,125 L100,114 L75,125 L86,100 L75,75 L100,86Z" />
      </g>

      {/* Center pivot dot */}
      <circle cx="100" cy="100" r="3.5" />
    </svg>
  );
}
