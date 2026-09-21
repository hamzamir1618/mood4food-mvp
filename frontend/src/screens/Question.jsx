import { useEffect, useState } from 'react';
import { num } from '../utils.js';

/** One open question: its chips, why it's worth asking, and a way past it. */
export default function Question({ question, step, onAnswer, onSkip, busy }) {
  const [picked, setPicked] = useState(-1);

  // The next question reuses this component, so the last answer has to be cleared.
  useEffect(() => setPicked(-1), [question.id, question.text]);

  const choose = (i, chip) => {
    if (busy || picked !== -1) return;
    setPicked(i);
    onAnswer(chip.value, chip.label);
  };

  return (
    <div className="screen question">
      <div className="q-bar">
        <div className="between pt-16">
          {/* Two is the limit the backend enforces (dialogue/questions.py MAX_QUESTIONS). */}
          <div className="lab accent">
            {question.id === 'relax' ? 'One thing to loosen' : `Question ${num(step)} of 02`}
          </div>
        </div>
        <div className="rule-ink draw" style={{ marginTop: 10 }} />
      </div>

      <div className="q-head">
        <h2 className="h2 mask pt-16">{question.text}</h2>
        {question.why && (
          <div className="body-serif muted rise pt-8" style={{ animationDelay: '140ms' }}>
            {question.why}
          </div>
        )}
        {question.id !== 'relax' && (
          <div className="q-numeral wide-only" aria-hidden="true">
            {num(step)}
          </div>
        )}
      </div>

      <div className="q-body">
        <div className="stagger pt-16">
          {question.chips.map((chip, i) => (
            <div key={chip.value} style={{ borderTop: '1px solid var(--rule)' }}>
              <button
                className={`row${picked === i ? ' is-on' : ''}`}
                onClick={() => choose(i, chip)}
                disabled={busy && picked !== i}
              >
                <span className="row-fill" />
                <span className="row-num">{num(i)}</span>
                <span className="row-label">{chip.label}</span>
                <span className="row-mark lab lab-sm">
                  {picked === i && busy ? <span className="spinner" /> : picked === i ? 'Chosen' : ''}
                </span>
              </button>
            </div>
          ))}
          <div style={{ borderTop: '1px solid var(--rule)' }} />
        </div>

        {/* The wait after an answer runs 2-4 seconds. Without this the screen looks frozen. */}
        {busy && (
          <div className="q-working lab lab-sm muted pt-12" role="status" aria-live="polite">
            <span className="spinner" />
            Working out your pick
          </div>
        )}

        <button
          className="btn btn-text rise"
          style={{ justifyContent: 'flex-start', marginTop: 16 }}
          onClick={onSkip}
          disabled={busy}
        >
          <span className="lab lab-sm">{question.skip_label || 'Just pick for me'} →</span>
        </button>
      </div>
    </div>
  );
}
