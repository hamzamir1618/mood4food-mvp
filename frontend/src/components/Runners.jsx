import { num, pct, placeLine, rupees } from '../utils.js';

const SHOWN = 4;

/**
 * The dishes that came second. The pick is one of a ranked shortlist, and showing the next
 * few — with their scores — is what makes that visible rather than asserted.
 */
export default function Runners({ candidates, winnerId }) {
  const runners = (candidates || []).filter((c) => c.dish_id !== winnerId).slice(0, SHOWN);
  if (!runners.length) return null;

  return (
    <section className="runners" aria-label="The next best dishes">
      <div className="between">
        <div className="lab accent">Also in the running</div>
        <div className="lab lab-sm muted">{runners.length} of {candidates.length - 1}</div>
      </div>
      <div className="rule-ink" style={{ marginTop: 8 }} />
      {runners.map((c, i) => (
        <article className="runner" key={c.dish_id}>
          <div className="runner-num bod-b">{num(i + 1)}</div>
          <div className="runner-body">
            <div className="runner-name">{c.name}</div>
            <div className="lab lab-sm muted runner-place">{placeLine(c)}</div>
            {c.exploration && <div className="lab lab-sm accent">Something different</div>}
          </div>
          <div className="runner-right">
            <div className="bod-b runner-match">{pct(c.u_total)}</div>
            <div className="lab lab-sm muted">{rupees(c.price_pkr)}</div>
          </div>
        </article>
      ))}
    </section>
  );
}
