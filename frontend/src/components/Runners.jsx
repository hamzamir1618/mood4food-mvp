import { useState } from 'react';
import { num, pct, placeLine, rupees } from '../utils.js';

const SHOWN = 4;
const TERMS = [
  ['u_budget', 'Price'],
  ['u_taste', 'Taste'],
  ['u_health', 'Health'],
];

/** One term's score as a badge; a term that sat out says so rather than showing a zero. */
function ScoreBadge({ value, label }) {
  const off = value === null || value === undefined;
  return (
    <span className={`score-badge${off ? ' is-off' : ''}`} title={off ? `${label} wasn't scored` : undefined}>
      <span className="score-badge-label">{label}</span>
      <b>{off ? '–' : pct(value)}</b>
    </span>
  );
}

const points = (n) => `${Math.abs(n)} point${Math.abs(n) === 1 ? '' : 's'}`;

/**
 * How a runner-up differs from the pick, in plain words: what it costs against it, how its
 * calories compare, which scores moved and by how much, and how far behind it finished.
 */
export function comparison(runner, winner) {
  const lines = [];
  const money = Math.round((runner.price_pkr || 0) - (winner.price_pkr || 0));
  if (money < 0) lines.push(`${rupees(-money)} cheaper`);
  else if (money > 0) lines.push(`${rupees(money)} dearer`);
  else lines.push('the same price');
  const kcal = (d) => d?.macros?.calories;
  if (kcal(runner) != null && kcal(winner) != null) {
    const diff = Math.round(kcal(runner) - kcal(winner));
    if (Math.abs(diff) >= 25) lines.push(`about ${Math.abs(diff)} kcal ${diff < 0 ? 'lighter' : 'heavier'}`);
  }
  const moved = [];
  for (const [key, label] of TERMS) {
    if (runner[key] == null || winner[key] == null) continue;
    const diff = pct(runner[key]) - pct(winner[key]);
    if (diff !== 0) moved.push(`${label.toLowerCase()} ${points(diff)} ${diff > 0 ? 'higher' : 'lower'}`);
  }
  const behind = pct(winner.u_total) - pct(runner.u_total);
  let overall;
  if ((winner.closeness || 0) > (runner.closeness || 0)) {
    overall = 'It meets less of what you asked for, which is why it sits below the pick.';
  } else if (behind > 0) {
    overall = `It finished ${points(behind)} behind overall.`;
  } else {
    overall = 'It finished level overall and lost on the tie-break.';
  }
  const scores = moved.length ? ` Scores: ${moved.join(', ')}.` : ' Its scores are the same as the pick.';
  return `Against ${winner.name}: ${lines.join(', ')}.${scores} ${overall}`;
}

/**
 * The dishes that came second. The pick is one of a ranked shortlist, and showing the next
 * few — with the scores behind each — is what makes that visible rather than asserted. Tapping
 * one says how it differs from the pick, and offers it instead.
 *
 * `badges` comes from the layout: {dish_id: "Your usual"}, for runners this person chose before
 * or that people with their taste chose.
 */
export default function Runners({ candidates, winner, badges, onRunner, busy }) {
  const [open, setOpen] = useState(null);
  const winnerId = winner?.dish_id;
  const runners = (candidates || []).filter((c) => c.dish_id !== winnerId).slice(0, SHOWN);
  if (!runners.length) return null;

  return (
    <section className="runners" aria-label="The next best dishes">
      <div className="between">
        <div className="lab accent">Also in the running</div>
        <div className="lab lab-sm muted">
          {runners.length} of {candidates.length - 1} · tap one to compare
        </div>
      </div>
      <div className="rule-ink" style={{ marginTop: 8 }} />
      {runners.map((c, i) => {
        const isOpen = open === c.dish_id;
        return (
          <article className={`runner${isOpen ? ' is-open' : ''}`} key={c.dish_id}>
            <button
              className="runner-head"
              onClick={() => setOpen(isOpen ? null : c.dish_id)}
              aria-expanded={isOpen}
            >
              <span className="runner-num bod-b">{num(i + 1)}</span>
              <span className="runner-body">
                <span className="runner-name">{c.name}</span>
                <span className="lab lab-sm muted runner-place">{placeLine(c)}</span>
                <span className="runner-tags">
                  {TERMS.map(([key, label]) => (
                    <ScoreBadge key={key} value={c[key]} label={label} />
                  ))}
                  {(c.meets || []).map((m) => (
                    <span className="badge is-inferred" key={m.id}>{m.words}</span>
                  ))}
                  {c.exploration && <span className="badge is-unchecked">Something different</span>}
                  {/* "Your usual", "Liked by similar tastes": what the server knows about this one. */}
                  {badges?.[c.dish_id] && <span className="badge is-unchecked">{badges[c.dish_id]}</span>}
                </span>
              </span>
              <span className="runner-right">
                <span className="bod-b runner-match">{pct(c.u_total)}</span>
                <span className="lab lab-sm muted">{rupees(c.price_pkr)}</span>
              </span>
            </button>
            {isOpen && (
              <div className="runner-compare rise" role="region" aria-label={`${c.name} against the pick`}>
                <p className="small" style={{ margin: 0 }}>{comparison(c, winner)}</p>
                {c.summary && <p className="small muted" style={{ margin: '6px 0 0' }}>{c.summary}</p>}
                {onRunner && (
                  <button className="lab lab-sm accent runner-take" onClick={() => onRunner(c.dish_id)} disabled={busy}>
                    Show me this one instead →
                  </button>
                )}
              </div>
            )}
          </article>
        );
      })}
    </section>
  );
}
