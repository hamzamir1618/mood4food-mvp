import { useEffect, useState } from 'react';
import * as api from '../api.js';
import { errorMessage, num } from '../utils.js';

const ALLERGENS = ['dairy', 'egg', 'fish', 'shellfish', 'gluten', 'nuts', 'soy', 'sesame'];
const DIETS = [
  ['none', 'No restriction'],
  ['vegetarian', 'Vegetarian'],
  ['vegan', 'Vegan'],
];
const GOALS = [
  ['balanced', 'Balanced', 'A sensible mix'],
  ['muscle_gain', 'Building muscle', 'More protein'],
  ['weight_loss', 'Losing weight', 'Fewer calories'],
  ['light', 'Eating light', 'Smaller, lighter meals'],
];
const STEPS = ['account', 'persona', 'dietary', 'goals'];

/**
 * Sign up, then the three things the backend keeps: the persona the taste model
 * starts from, the rules that are never relaxed, and what you're eating for.
 * Each step saves as you leave it, so nothing is stored without you agreeing to it.
 */
export default function Setup({ onDone, onSignedIn, toast }) {
  const [step, setStep] = useState('welcome'); // welcome · signin · account · persona · dietary · goals
  const [busy, setBusy] = useState(false);
  const [personas, setPersonas] = useState({});
  const [form, setForm] = useState({ display_name: '', email: '', password: '' });
  const [persona, setPersona] = useState('balanced');
  const [allergies, setAllergies] = useState([]);
  const [diet, setDiet] = useState('none');
  const [halal, setHalal] = useState(false);
  const [goal, setGoal] = useState('balanced');
  const [spend, setSpend] = useState('');

  useEffect(() => {
    api.personas().then(setPersonas).catch(() => {});
  }, []);

  const run = async (work, after) => {
    setBusy(true);
    try {
      const result = await work();
      after?.(result);
    } catch (err) {
      toast(errorMessage(err), 'error');
    } finally {
      setBusy(false);
    }
  };

  const createAccount = () =>
    run(
      () => api.register({ ...form, persona }),
      (r) => {
        onSignedIn(r.user);
        toast(r.guest_events_claimed ? 'Your earlier picks moved across.' : 'Account created.');
        setStep('dietary');
      },
    );

  const signIn = () =>
    run(
      () => api.login(form.email, form.password),
      (r) => {
        onSignedIn(r.user);
        onDone();
      },
    );

  const saveDietary = () =>
    run(
      () => api.setDietary({ allergies, diet, halal_only: halal }),
      () => setStep('goals'),
    );

  const saveGoals = () =>
    run(
      () => api.setGoals({ goal, typical_spend_pkr: spend ? Number(spend) : null }),
      () => {
        toast('Saved. You can change any of it later.');
        onDone();
      },
    );

  const stepIndex = STEPS.indexOf(step);

  return (
    <div className="screen">
      {stepIndex >= 0 && (
        <>
          <div className="between pt-12">
            <div className="lab accent">
              Step {num(stepIndex)} of {String(STEPS.length).padStart(2, '0')}
            </div>
            <button className="lab lab-sm muted" onClick={onDone}>
              Skip for now
            </button>
          </div>
          <div className="rule-ink draw" style={{ marginTop: 8 }} />
        </>
      )}

      {step === 'welcome' && (
        <>
          <h1 className="h1 mask pt-24">
            Tell me your
            <br />
            mood. I'll find
            <br />
            the <span style={{ fontStyle: 'italic' }}>dish</span>.
          </h1>
          <p className="body-serif rise pt-16" style={{ margin: 0 }}>
            Picks from real Islamabad menus, weighed for taste, budget and health, with the reasons
            spelled out.
          </p>
          <div className="mt-auto pt-24" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button className="btn btn-accent btn-wide" onClick={() => setStep('account')}>
              <span className="lab">Create an account</span>
              <span className="bod" style={{ fontSize: 20 }}>→</span>
            </button>
            <button className="btn btn-line" onClick={() => setStep('signin')}>
              <span className="lab">Sign in</span>
            </button>
            <button className="btn btn-text" onClick={onDone}>
              <span className="lab lab-sm">Continue as a guest</span>
            </button>
          </div>
        </>
      )}

      {(step === 'account' || step === 'signin') && (
        <>
          <h2 className="h2 mask pt-16">{step === 'signin' ? 'Welcome back.' : 'Create your account.'}</h2>
          <p className="small muted pt-8">
            {step === 'signin'
              ? 'Your picks and what I learned are waiting.'
              : 'So your picks, and what I learn from them, stay with you.'}
          </p>
          <div className="stack gap-14 pt-16">
            {step === 'account' && (
              <label className="stack gap-6">
                <span className="lab lab-sm">Your name (optional)</span>
                <input
                  className="field-box"
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                />
              </label>
            )}
            <label className="stack gap-6">
              <span className="lab lab-sm">Email</span>
              <input
                className="field-box"
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </label>
            <label className="stack gap-6">
              <span className="lab lab-sm">Password</span>
              <input
                className="field-box"
                type="password"
                autoComplete={step === 'signin' ? 'current-password' : 'new-password'}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
              {step === 'account' && <span className="lab lab-sm muted">At least 10 characters.</span>}
            </label>
          </div>
          <div className="mt-auto pt-24" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button
              className="btn btn-accent"
              onClick={step === 'signin' ? signIn : () => setStep('persona')}
              disabled={busy || !form.email || !form.password}
            >
              <span className="lab">{step === 'signin' ? 'Sign in' : 'Continue'}</span>
              {busy && <span className="spinner" />}
            </button>
            <button className="btn btn-text" onClick={() => setStep(step === 'signin' ? 'account' : 'signin')}>
              <span className="lab lab-sm">
                {step === 'signin' ? 'New here? Create an account' : 'I already have an account'}
              </span>
            </button>
          </div>
        </>
      )}

      {step === 'persona' && (
        <>
          <h2 className="h2 mask pt-16">Where should I start?</h2>
          <p className="small muted pt-8">
            Pick the closest. It's only a starting point: I learn from the dishes you approve.
          </p>
          <div className="scroll-y pt-12" style={{ flex: 1 }}>
            {Object.entries(personas).map(([key, p], i) => (
              <div key={key} style={{ borderTop: '1px solid var(--rule)' }}>
                <button className={`row${persona === key ? ' is-on' : ''}`} onClick={() => setPersona(key)}>
                  <span className="row-fill" />
                  <span className="row-num">{num(i)}</span>
                  <span className="stack" style={{ position: 'relative', flex: 1 }}>
                    <span className="row-label" style={{ fontSize: 22 }}>{p.display_name}</span>
                    <span className="lab lab-sm" style={{ opacity: 0.7 }}>{p.description}</span>
                  </span>
                  <span className="row-mark lab lab-sm">{persona === key ? 'Chosen' : ''}</span>
                </button>
              </div>
            ))}
            <div style={{ borderTop: '1px solid var(--rule)' }} />
          </div>
          <button className="btn btn-accent mt-auto" onClick={createAccount} disabled={busy}>
            <span className="lab">Create account</span>
            {busy && <span className="spinner" />}
          </button>
        </>
      )}

      {step === 'dietary' && (
        <>
          <h2 className="h2 mask pt-16">Anything you can't eat?</h2>
          <p className="small pt-8" style={{ fontWeight: 600 }}>
            These are hard rules. I never relax them, even when little fits.
          </p>

          <div className="lab lab-sm pt-16">Allergies</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, paddingTop: 8 }}>
            {ALLERGENS.map((a) => {
              const on = allergies.includes(a);
              return (
                <button
                  key={a}
                  className="lab"
                  onClick={() => setAllergies(on ? allergies.filter((x) => x !== a) : [...allergies, a])}
                  style={{
                    minHeight: 44,
                    padding: '0 14px',
                    border: `1.5px solid ${on ? 'var(--ink)' : 'var(--rule)'}`,
                    background: on ? 'var(--ink)' : 'var(--paper)',
                    color: on ? 'var(--paper)' : 'var(--ink)',
                  }}
                >
                  {on ? '✓ ' : ''}
                  {a}
                </button>
              );
            })}
          </div>

          <div className="lab lab-sm pt-24">Diet</div>
          <div style={{ display: 'flex', gap: 8, paddingTop: 8 }}>
            {DIETS.map(([value, label]) => (
              <button
                key={value}
                className="lab"
                onClick={() => setDiet(value)}
                style={{
                  flex: 1,
                  minHeight: 48,
                  border: `1.5px solid ${diet === value ? 'var(--ink)' : 'var(--rule)'}`,
                  background: diet === value ? 'var(--ink)' : 'var(--paper)',
                  color: diet === value ? 'var(--paper)' : 'var(--ink)',
                }}
              >
                {label}
              </button>
            ))}
          </div>

          <button
            className="between pt-24"
            onClick={() => setHalal(!halal)}
            style={{ width: '100%', textAlign: 'left', paddingBottom: 14, borderBottom: '1px solid var(--rule)' }}
          >
            <span className="stack gap-6">
              <span style={{ fontSize: 18, fontWeight: 600 }}>Halal only</span>
              <span className="small muted">Leave out anything not marked halal.</span>
            </span>
            <span
              className="lab lab-sm"
              style={{
                minHeight: 44,
                display: 'flex',
                alignItems: 'center',
                padding: '0 14px',
                border: `1.5px solid ${halal ? 'var(--ink)' : 'var(--rule)'}`,
                background: halal ? 'var(--ink)' : 'var(--paper)',
                color: halal ? 'var(--paper)' : 'var(--ink)',
              }}
            >
              {halal ? 'On' : 'Off'}
            </span>
          </button>

          <button className="btn btn-accent mt-auto" onClick={saveDietary} disabled={busy}>
            <span className="lab">Continue</span>
            {busy && <span className="spinner" />}
          </button>
        </>
      )}

      {step === 'goals' && (
        <>
          <h2 className="h2 mask pt-16">What are you eating for?</h2>
          <p className="small muted pt-8">It changes how a dish's calories and protein are weighed.</p>
          <div className="pt-12">
            {GOALS.map(([value, label, note], i) => (
              <div key={value} style={{ borderTop: '1px solid var(--rule)' }}>
                <button className={`row${goal === value ? ' is-on' : ''}`} onClick={() => setGoal(value)}>
                  <span className="row-fill" />
                  <span className="row-num">{num(i)}</span>
                  <span className="stack" style={{ position: 'relative', flex: 1 }}>
                    <span className="row-label" style={{ fontSize: 22 }}>{label}</span>
                    <span className="lab lab-sm" style={{ opacity: 0.7 }}>{note}</span>
                  </span>
                  <span className="row-mark lab lab-sm">{goal === value ? 'Chosen' : ''}</span>
                </button>
              </div>
            ))}
            <div style={{ borderTop: '1px solid var(--rule)' }} />
          </div>

          <div className="pt-24">
            <div className="lab lab-sm">Usual spend on a meal (optional)</div>
            <input
              className="field"
              inputMode="numeric"
              value={spend}
              onChange={(e) => setSpend(e.target.value.replace(/[^\d]/g, ''))}
              placeholder="Rs 1,200"
              style={{ marginTop: 6 }}
            />
            <div className="lab lab-sm muted pt-8">Used when you don't mention a budget.</div>
          </div>

          <button className="btn btn-accent mt-auto" onClick={saveGoals} disabled={busy}>
            <span className="lab">Finish</span>
            {busy && <span className="spinner" />}
          </button>
        </>
      )}
    </div>
  );
}
