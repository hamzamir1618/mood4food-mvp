import { useCallback, useEffect, useRef, useState } from 'react';
import * as api from './api.js';
import { errorMessage } from './utils.js';
import { useToast } from './components/Toast.jsx';
import Masthead from './components/Masthead.jsx';
import Home from './screens/Home.jsx';
import Question from './screens/Question.jsx';
import Pick from './screens/Pick.jsx';
import Scores from './screens/Scores.jsx';
import Done from './screens/Done.jsx';
import Trouble from './screens/Trouble.jsx';
import Areas from './screens/Areas.jsx';
import Setup from './screens/Setup.jsx';
import Profile from './screens/Profile.jsx';
import About from './screens/About.jsx';

const LOCATION_KEY = 'm4f.location';
const SEEN_KEY = 'm4f.seen';

const remember = (key, value) => {
  try {
    localStorage.setItem(key, value);
  } catch (e) {
    /* a browser that refuses storage still works, it just forgets */
  }
};

/**
 * /alternate rebuilds the winner from a shorter set of fields, so the restaurant and
 * summary can be missing. The shortlist still has them, so fill them back in.
 */
function withPlace(blueprint) {
  const winner = blueprint?.winning_dish;
  if (!winner) return blueprint;
  const full = (blueprint.top_candidates || []).find((c) => c.dish_id === winner.dish_id);
  return full ? { ...blueprint, winning_dish: { ...full, ...winner, ...pickPlace(full, winner) } } : blueprint;
}

const pickPlace = (full, winner) => ({
  restaurant_name: winner.restaurant_name ?? full.restaurant_name,
  restaurant_area: winner.restaurant_area ?? full.restaurant_area,
  restaurant_lat: winner.restaurant_lat ?? full.restaurant_lat,
  restaurant_lng: winner.restaurant_lng ?? full.restaurant_lng,
  distance_km: winner.distance_km ?? full.distance_km,
  summary: winner.summary || full.summary,
  serves_min: winner.serves_min ?? full.serves_min,
  serves_max: winner.serves_max ?? full.serves_max,
});

function savedLocation() {
  try {
    const raw = localStorage.getItem(LOCATION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

export default function App() {
  const showToast = useToast();

  const [phase, setPhase] = useState('home'); // home · question · pick · done
  const [question, setQuestion] = useState(null);
  const [blueprint, setBlueprint] = useState(null);
  const [refinements, setRefinements] = useState([]);
  const [asked, setAsked] = useState(0);
  const [busy, setBusy] = useState(false);
  const [scoresOpen, setScoresOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [location, setLocation] = useState(savedLocation);
  const [query, setQuery] = useState('');
  const [trouble, setTrouble] = useState(null); // {kind: 'offline' | 'nomatch', message}
  const [areasOpen, setAreasOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  // A first-time visitor lands on the product, not on a sign-up wall. Setup stays one tap
  // away on the home screen ("Sign in →"), which is also how the account demo is reached.
  const [setupOpen, setSetupOpen] = useState(false);
  const rejected = useRef([]);

  const keepLocation = useCallback((place) => {
    setLocation(place);
    remember(LOCATION_KEY, JSON.stringify(place));
  }, []);

  const finishSetup = useCallback(() => {
    remember(SEEN_KEY, '1');
    setSetupOpen(false);
  }, []);

  useEffect(() => {
    api.me().then((r) => setUser(r.user)).catch(() => {});
  }, []);

  /** Every reply is either a question or a recommendation; both carry a line to show. */
  const apply = useCallback(
    (reply) => {
      if (reply.reply) showToast(reply.reply);
      if (reply.type === 'question') {
        setQuestion(reply.question);
        setPhase('question');
        return;
      }
      setQuestion(null);
      if (!reply.recommendation?.winning_dish) {
        // Every rule held and nothing was left; the screen says so rather than relaxing one.
        setTrouble({ kind: 'nomatch', message: reply.recommendation?.relaxation_notice });
        setPhase('trouble');
        return;
      }
      setBlueprint(withPlace(reply.recommendation));
      setRefinements(reply.refinements || []);
      setPhase('pick');
    },
    [showToast],
  );

  const run = useCallback(
    async (work) => {
      setBusy(true);
      try {
        return await work();
      } catch (err) {
        // A failed fetch never reaches the server, so it gets a screen rather than a toast.
        if (err?.name === 'TypeError' || err?.status === undefined) {
          setTrouble({ kind: 'offline' });
          setPhase('trouble');
        } else {
          showToast(errorMessage(err), 'error');
        }
        return null;
      } finally {
        setBusy(false);
      }
    },
    [showToast],
  );

  const start = useCallback(
    async (text, from) => {
      setQuery(text);
      setAsked(0);
      setTrouble(null);
      rejected.current = [];
      // The location is sent with the request that uses it: distances are measured
      // during the query, not afterwards.
      let place = from || location;
      if (!place) {
        place = await api.locate(6000);
        if (place) keepLocation(place);
      }
      const reply = await run(() => api.chat(place ? { text, location: place } : { text }));
      if (reply) apply(reply);
    },
    [apply, keepLocation, location, run],
  );

  const answer = useCallback(
    async (value) => {
      const open = question;
      if (!open) return;
      setAsked((n) => n + 1);
      const reply = await run(() => api.chat({ answer: { question: open.id, value } }));
      if (reply) apply(reply);
    },
    [apply, question, run],
  );

  const skip = useCallback(async () => {
    const reply = await run(() => api.chat({ skip: true }));
    if (reply) apply(reply);
  }, [apply, run]);

  const refine = useCallback(
    async (critique) => {
      const reply = await run(() => api.chat({ critique }));
      if (reply) apply(reply);
    },
    [apply, run],
  );

  const nextDish = useCallback(async () => {
    const current = blueprint?.winning_dish?.dish_id;
    if (current) rejected.current = [...rejected.current, current];
    const next = await run(() => api.alternate(rejected.current));
    if (!next) return;
    if (next.no_more_alternates) {
      showToast("That's every dish that fitted. Try a refinement instead.");
      return;
    }
    setBlueprint(withPlace(next));
  }, [blueprint, run, showToast]);

  const choose = useCallback(async () => {
    const dish = blueprint?.winning_dish;
    if (!dish?.dish_id) return;
    const result = await run(() => api.approve(dish.dish_id));
    if (!result) return;
    if (result.note) showToast(result.note);
    setPhase('done');
  }, [blueprint, run, showToast]);

  const restart = useCallback(() => {
    rejected.current = [];
    setBlueprint(null);
    setQuestion(null);
    setAsked(0);
    setTrouble(null);
    setPhase('home');
  }, []);

  const back = useCallback(() => {
    if (phase === 'question') restart();
    else if (phase === 'pick') restart();
    else if (phase === 'done') setPhase('pick');
  }, [phase, restart]);

  const left =
    phase === 'home' ? 'Islamabad edition' : phase === 'done' ? 'Your order' : 'Finding your dish';
  // The right side stays the place you're eating from; the step is on the screen itself.
  const right = location?.label || (phase === 'home' ? 'Set area' : 'Islamabad');

  if (setupOpen) {
    return (
      <div className="app">
        <Masthead left="Welcome" right="Islamabad" />
        <Setup onDone={finishSetup} onSignedIn={setUser} toast={showToast} />
      </div>
    );
  }

  if (profileOpen) {
    return (
      <div className="app">
        <Masthead left="Your account" right={location?.label || 'Islamabad'} />
        <Profile
          user={user}
          onClose={() => setProfileOpen(false)}
          onSignedOut={() => {
            setUser(null);
            setProfileOpen(false);
            showToast('Signed out.');
          }}
          toast={showToast}
        />
      </div>
    );
  }

  return (
    <div className="app">
      <Masthead
        left={left}
        right={right}
        onBack={phase === 'home' ? null : back}
        onProfile={() => setAreasOpen(true)}
      />

      {phase === 'home' && (
        <div className="between" style={{ paddingTop: 10 }}>
          <button className="lab lab-sm muted" onClick={() => setAreasOpen(true)}>
            {location ? `Measuring from ${location.label}` : 'No area set'}
          </button>
          <button
            className="lab lab-sm accent"
            onClick={() => (user ? setProfileOpen(true) : setSetupOpen(true))}
          >
            {user ? 'Your account →' : 'Sign in →'}
          </button>
        </div>
      )}

      {phase === 'home' && (
        <Home onStart={start} busy={busy} initialQuery={query} onAbout={() => setAboutOpen(true)} />
      )}

      {phase === 'question' && question && (
        <Question
          key={question.id}
          question={question}
          step={asked}
          onAnswer={answer}
          onSkip={skip}
          busy={busy}
        />
      )}

      {phase === 'pick' && blueprint && (
        <Pick
          key={blueprint.winning_dish?.dish_id || 'pick'}
          blueprint={blueprint}
          refinements={refinements}
          rank={`No. ${rejected.current.length + 1} of ${blueprint.top_candidates?.length || 1}`}
          onRefine={refine}
          onNext={nextDish}
          onChoose={choose}
          onScores={() => setScoresOpen(true)}
          busy={busy}
        />
      )}

      {phase === 'done' && <Done dish={blueprint?.winning_dish} onRestart={restart} />}

      {phase === 'trouble' && trouble && (
        <Trouble
          kind={trouble.kind}
          message={trouble.message}
          onRetry={() => (query ? start(query) : restart())}
          onRestart={restart}
        />
      )}

      {scoresOpen && blueprint && <Scores blueprint={blueprint} onClose={() => setScoresOpen(false)} />}

      {aboutOpen && <About onClose={() => setAboutOpen(false)} />}

      {areasOpen && (
        <Areas
          current={location}
          onPick={(place) => {
            keepLocation(place);
            setAreasOpen(false);
            // Distances are worked out when a request runs, so a request already on
            // screen is asked again from the new place.
            if (query && phase !== 'home') {
              showToast(`Measuring from ${place.label}.`);
              start(query, place);
            } else {
              showToast(`Measuring from ${place.label}.`);
            }
          }}
          onClose={() => setAreasOpen(false)}
        />
      )}
    </div>
  );
}
