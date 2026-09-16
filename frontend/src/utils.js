/* Turning the backend's numbers and lists into the words the screens show. */

export const pct = (u) => Math.round(Math.max(0, Math.min(1, u ?? 0)) * 100);

export function rupees(value) {
  if (value === null || value === undefined) return '';
  return `Rs ${Math.round(value).toLocaleString('en-PK')}`;
}

export function serves(min, max) {
  if (!min && !max) return '';
  const low = min ?? max;
  const high = max ?? min;
  if (low === high) return `Serves ${low}`;
  return `Serves ${low}–${high}`;
}

export function distance(km) {
  if (km === null || km === undefined) return '';
  return km >= 10 ? `${km.toFixed(1)} km` : `about ${km.toFixed(1)} km`;
}

/** "Tiger Temple · F-7 · about 3.8 km", skipping whatever isn't known. */
export function placeLine(dish) {
  return [dish?.restaurant_name, dish?.restaurant_area, distance(dish?.distance_km)]
    .filter(Boolean)
    .join(' · ');
}

/** Allergens are never guessed at: an unknown list says so rather than saying none. */
export function allergenLine(allergens) {
  if (allergens === null || allergens === undefined) return "The allergens aren't known.";
  if (!allergens.length) return 'No allergens listed.';
  const names = allergens.map((a) => String(a).toLowerCase());
  const last = names.pop();
  return names.length ? `Contains ${names.join(', ')} and ${last}.` : `Contains ${last}.`;
}

export function joinList(items) {
  const list = (items || []).map((i) => String(i));
  if (!list.length) return '';
  const last = list.pop();
  return list.length ? `${list.join(', ')} and ${last}` : last;
}

/** The scored terms, in the order the screens show them. Distance needs a location. */
export function scoreRows(blueprint) {
  const u = blueprint?.utility_breakdown || {};
  const reasons = blueprint?.winning_dish?.reasons || {};
  return [
    ['Taste', u.u_taste, reasons.taste],
    ['Budget', u.u_budget, reasons.budget],
    ['Health', u.u_health, reasons.health],
    ['Distance', u.u_distance, reasons.distance],
  ]
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([label, value, text]) => ({ label, value: pct(value), text: text || '' }));
}

export function matchOf(blueprint) {
  return pct(blueprint?.utility_breakdown?.u_total);
}

export function errorMessage(err) {
  if (!err) return 'Something went wrong.';
  if (err.status === 0 || err.name === 'TypeError') return "Can't reach Mood4Food right now.";
  return err.message || 'Something went wrong.';
}

export const num = (i) => String(i + 1).padStart(2, '0');
