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
    <div className="screen">
      <div className="between pt-16">
        <div className="lab accent">Question {num(step)} of 03</div>
      </div>
      <div className="rule-ink draw" style={{ marginTop: 10 }} />

      <h2 className="h2 mask pt-16">{question.text}</h2>
      {question.why && (
        <div className="body-serif muted rise pt-8" style={{ animationDelay: '140ms' }}>
          {question.why}
        </div>
      )}

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
              <span className="row-mark lab lab-sm">{picked === i ? 'Chosen' : ''}</span>
            </button>
          </div>
        ))}
        <div style={{ borderTop: '1px solid var(--rule)' }} />
      </div>

      <button className="btn btn-text rise" style={{ justifyContent: 'flex-start', marginTop: 16 }} onClick={onSkip} disabled={busy}>
        <span className="lab lab-sm">{question.skip_label || 'Just pick for me'} →</span>
      </button>
    </div>
  );
}
