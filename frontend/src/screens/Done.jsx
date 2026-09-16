import { distance, placeLine, rupees } from '../utils.js';

function mapsUrl(dish) {
  const target =
    dish.restaurant_lat && dish.restaurant_lng
      ? `${dish.restaurant_lat},${dish.restaurant_lng}`
      : [dish.restaurant_name, dish.restaurant_area, 'Islamabad'].filter(Boolean).join(' ');
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(target)}`;
}

const pandaUrl = (dish) =>
  `https://www.foodpanda.pk/search?q=${encodeURIComponent(dish.restaurant_name || dish.name || '')}`;

/** Settled: what was chosen, where it is, and the two ways to go and get it. */
export default function Done({ dish, onRestart }) {
  const km = distance(dish?.distance_km);

  return (
    <div className="screen">
      <div className="lab accent rise pt-16">Settled</div>
      <div className="rule-thick draw" style={{ marginTop: 8 }} />

      <h2 className="h2 mask pt-16">{dish?.name}</h2>
      {(dish?.restaurant_name || km) && (
        <div className="body-serif rise pt-12" style={{ fontStyle: 'italic' }}>
          {[dish?.restaurant_name, dish?.restaurant_area].filter(Boolean).join(', ')}
          {km ? `${dish?.restaurant_name ? '. ' : ''}${km[0].toUpperCase()}${km.slice(1)} from you.` : '.'}
        </div>
      )}

      {dish?.image_url && (
        <div className="photo wipe" style={{ height: 190, marginTop: 18 }}>
          <img src={dish.image_url} alt={dish.name} />
        </div>
      )}

      <div className="between pt-16">
        <div className="bod-b" style={{ fontSize: 30 }}>{rupees(dish?.price_pkr)}</div>
        <div className="lab lab-sm muted">Pay at the restaurant</div>
      </div>

      <div className="mt-auto pt-24" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <a className="btn btn-accent btn-wide" href={mapsUrl(dish || {})} target="_blank" rel="noreferrer">
          <span className="lab">Get directions</span>
          <span className="bod" style={{ fontSize: 20 }}>→</span>
        </a>
        <a className="btn btn-line btn-wide" href={pandaUrl(dish || {})} target="_blank" rel="noreferrer">
          <span className="lab">Find it on foodpanda</span>
          <span className="bod" style={{ fontSize: 20 }}>→</span>
        </a>
        <button className="btn btn-text" onClick={onRestart}>
          <span className="lab lab-sm">Start over</span>
        </button>
      </div>
    </div>
  );
}
