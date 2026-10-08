/**
 * Monoline stamps for the evidence panel: one per facet the server names
 * (ui/provenance.py — row, name, price, ingredients, allergens, nutrition, taste, serves,
 * source). Drawn in the page's ink at a hairline weight, so they read as printed marks on the
 * broadsheet rather than as app iconography, and they carry no colour of their own — the badge
 * beside them is what says how strong the evidence is.
 *
 * `aria-hidden`: every stamp sits beside its own heading, so naming it again is noise to a
 * screen reader.
 */

const PATHS = {
  // A photograph of a menu: a frame, two lines of print, a folded corner.
  row: (
    <>
      <rect x="3.5" y="4.5" width="17" height="15" rx="1" />
      <path d="M7 9h7M7 12.5h10M7 16h5" />
    </>
  ),
  // A hand correcting it.
  name: (
    <>
      <path d="M4 20h4l10.5-10.5a2 2 0 0 0-3-3L5 17v3z" />
      <path d="M14.5 6.5l3 3" />
    </>
  ),
  // Which pile it was sorted into.
  kind: (
    <>
      <rect x="3.5" y="4" width="7" height="7" rx="1" />
      <rect x="13.5" y="4" width="7" height="7" rx="1" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1" />
      <path d="M17 13.5v7M13.5 17h7" />
    </>
  ),
  // A plate, from above.
  dish: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4.5" />
    </>
  ),
  // A shopfront with an awning.
  store: (
    <>
      <path d="M4 9.5V20h16V9.5" />
      <path d="M3 9.5l1.5-5h15l1.5 5c0 1.4-1.1 2.5-2.5 2.5S16 10.9 16 9.5c0 1.4-1.1 2.5-2.5 2.5h-3C9.1 12 8 10.9 8 9.5 8 10.9 6.9 12 5.5 12S3 10.9 3 9.5z" />
      <path d="M10 20v-4.5h4V20" />
    </>
  ),
  // A person, and a tick beside them.
  checked: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
      <path d="M15.5 10.5l2 2 4-4.5" />
    </>
  ),
  // A target: the dishes in the running.
  target: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.5" />
    </>
  ),
  // An eye, struck through: kept, but never shown.
  hidden: (
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
      <circle cx="12" cy="12" r="3" />
      <path d="M4 20L20 4" />
    </>
  ),
  // A drop of oil.
  fat: (
    <>
      <path d="M12 3.5c3.5 4.6 6 8 6 10.8a6 6 0 0 1-12 0C6 11.5 8.5 8.1 12 3.5z" />
      <path d="M9.2 14.5a2.9 2.9 0 0 0 2.8 2.8" />
    </>
  ),
  // A leaf.
  vegan: (
    <>
      <path d="M5 19c0-8 5-13.5 14.5-14.5C19 14 13.5 19 5 19z" />
      <path d="M5 19l8.5-8.5" />
    </>
  ),
  // What has to be absent: pork, alcohol.
  halal: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M6 18L18 6" />
    </>
  ),
  // Where it sits on the map.
  where: (
    <>
      <path d="M12 21c4-4.5 6-7.7 6-10.4a6 6 0 1 0-12 0C6 13.3 8 16.5 12 21z" />
      <circle cx="12" cy="10.5" r="2.2" />
    </>
  ),
  // A price tag.
  price: (
    <>
      <path d="M12.5 3.5H20v7.5l-9 9-8-8 9.5-8.5z" />
      <circle cx="16.5" cy="7.5" r="1.4" />
    </>
  ),
  // What went into it: a listing.
  ingredients: (
    <>
      <circle cx="5" cy="7" r="1.2" />
      <circle cx="5" cy="12" r="1.2" />
      <circle cx="5" cy="17" r="1.2" />
      <path d="M9 7h11M9 12h11M9 17h7" />
    </>
  ),
  // What has to be kept out.
  allergens: (
    <>
      <path d="M12 3.5l7 2.5v6c0 4-3 7-7 8.5-4-1.5-7-4.5-7-8.5V6l7-2.5z" />
      <path d="M12 8.5v4.5M12 15.8v.2" />
    </>
  ),
  // An estimate, on a dial.
  nutrition: (
    <>
      <path d="M4 17a8 8 0 1 1 16 0" />
      <path d="M12 17l4.5-5" />
      <circle cx="12" cy="17" r="1.3" />
    </>
  ),
  // Flavour: a drop of heat.
  // A chilli: the flavour of a dish. (A drop now means the oil in it.)
  taste: (
    <>
      <path d="M15.5 8.5c2.5 1 3.5 3.5 2.5 6.5-1.5 4.5-7 6.5-13.5 5.5 4.5-1.5 7-4.5 7.5-8.5.3-2.5 1.5-3.8 3.5-3.5z" />
      <path d="M15.5 8.5c0-2 .8-3.5 2.5-4.5" />
    </>
  ),
  // How many it feeds.
  serves: (
    <>
      <circle cx="9" cy="8" r="2.6" />
      <path d="M3.5 19c0-3 2.5-5 5.5-5s5.5 2 5.5 5" />
      <path d="M16 6.5a2.6 2.6 0 0 1 0 5.2M17.5 14.4c1.8.7 3 2.4 3 4.6" />
    </>
  ),
  // Where the row came from.
  source: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M3.5 12h17M12 3.5c2.6 2.4 4 5.4 4 8.5s-1.4 6.1-4 8.5c-2.6-2.4-4-5.4-4-8.5s1.4-6.1 4-8.5z" />
    </>
  ),
};

export default function Glyph({ name, size = 20 }) {
  const path = PATHS[name];
  if (!path) return null;
  return (
    <svg
      className="glyph"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {path}
    </svg>
  );
}
