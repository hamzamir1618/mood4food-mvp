import { useEffect, useMemo, useState } from 'react';
import * as api from '../api.js';
import { num } from '../utils.js';

/**
 * Where you're eating from. The list is every area with a located restaurant
 * (GET /areas); the point it carries is what distances are measured from.
 */
export default function Areas({ current, onPick, onClose }) {
  const [areas, setAreas] = useState(null);
  const [failed, setFailed] = useState(false);
  const [filter, setFilter] = useState('');
  const [locating, setLocating] = useState(false);

  useEffect(() => {
    api
      .areas()
      .then((r) => setAreas(r.areas || []))
      .catch(() => setFailed(true));
  }, []);

  const shown = useMemo(() => {
    const list = areas || [];
    const needle = filter.trim().toLowerCase();
    return needle ? list.filter((a) => a.area.toLowerCase().includes(needle)) : list;
  }, [areas, filter]);

  const useMyLocation = async () => {
    setLocating(true);
    const place = await api.locate();
    setLocating(false);
    if (place) onPick(place);
    else setFailed(true);
  };

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className="sheet" role="dialog" aria-label="Where are you eating from?">
        <div className="between">
          <div className="lab accent">Where are you eating from?</div>
          <button className="lab lab-sm muted" onClick={onClose}>
            Close ✕
          </button>
        </div>
        <div className="small muted pt-8">
          It only decides how far each place is. Nothing is shared with the restaurants.
        </div>

        <button className="btn btn-line btn-wide" style={{ marginTop: 14 }} onClick={useMyLocation} disabled={locating}>
          <span className="lab">{locating ? 'Asking your browser' : 'Use my location'}</span>
          {locating ? <span className="spinner" /> : <span className="bod" style={{ fontSize: 20 }}>→</span>}
        </button>

        <input
          className="field"
          style={{ marginTop: 18 }}
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Find an area"
          aria-label="Find an area"
        />

        <div style={{ paddingTop: 10 }}>
          {areas === null && !failed && <div className="lab lab-sm muted pt-12">Loading the areas</div>}
          {failed && areas === null && (
            <div className="small pt-12">The areas couldn't be loaded. You can still ask without a location.</div>
          )}
          {shown.map((a, i) => {
            const on = current?.label === a.area;
            return (
              <div key={a.area} style={{ borderTop: '1px solid var(--rule)' }}>
                <button
                  className={`row${on ? ' is-on' : ''}`}
                  onClick={() => onPick({ lat: a.lat, lng: a.lng, label: a.area })}
                >
                  <span className="row-fill" />
                  <span className="row-num">{num(i)}</span>
                  <span className="row-label">{a.area}</span>
                  <span className="row-mark lab lab-sm">{on ? 'Chosen' : ''}</span>
                </button>
              </div>
            );
          })}
          {areas !== null && shown.length === 0 && (
            <div className="small muted pt-12">No area goes by that name.</div>
          )}
        </div>
      </div>
    </>
  );
}
