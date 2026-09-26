import Runners from './Runners.jsx';
import Weights from './Weights.jsx';
import { allergenLine, placeLine, rupees, serves } from '../utils.js';

/**
 * The blocks a Pick screen is made of. The server sends a layout — which blocks, in which
 * column, in what order, drawn how — and this is the catalogue it names (docs/SERVER_DRIVEN_UI.md).
 *
 * Each block draws the same markup the fixed screen always used, so a layout with no adaptations
 * is the screen we had. A block type this file doesn't know is skipped, which is what lets the
 * server add one before the frontend can draw it.
 */

const REASON_KEYS = { Taste: 'taste', Budget: 'budget', Health: 'health', Distance: 'distance' };

function Match({ ctx }) {
  return (
    <div className="match-row">
      <div className="match-num">{ctx.shown}</div>
      <div style={{ paddingTop: 8 }}>
        <div className="lab">Match</div>
        <div className="lab lab-sm muted">Out of 100</div>
      </div>
      <div className="grow" />
      <button
        className="lab accent"
        data-nodrag="1"
        onClick={ctx.onScores}
        style={{ paddingTop: 8, textAlign: 'right' }}
      >
        The scores
        <br />
        <span className="bod" style={{ fontSize: 16 }}>
          ↓
        </span>
      </button>
    </div>
  );
}

function Name({ ctx }) {
  return <h2 className="h2 pick-name mask pt-8">{ctx.dish.name}</h2>;
}

function Place({ ctx }) {
  return <div className="lab rise pt-12">{placeLine(ctx.dish)}</div>;
}

/** `headline` is for someone counting the cost: the price leads, with the price per person. */
function Price({ ctx, block }) {
  const headline = block.variant === 'headline';
  const each = block.props?.per_person;
  return (
    <div>
      <div className="rule draw" style={{ marginTop: 10 }} />
      <div className="between" style={{ padding: '8px 0' }}>
        <div className={`bod-b pick-price${headline ? ' is-headline' : ''}`}>
          {rupees(ctx.dish.price_pkr)}
        </div>
        <div className="lab lab-sm muted">
          {each ? `${rupees(each)} each` : serves(ctx.dish.serves_min, ctx.dish.serves_max)}
        </div>
      </div>
      <div className="rule draw" />
    </div>
  );
}

function Photo({ ctx }) {
  if (!ctx.hasPhoto) return null;
  return (
    <div>
      <div className="photo pick-photo wipe" style={{ marginTop: 12 }}>
        <img
          src={ctx.dish.image_url}
          alt={ctx.dish.name}
          draggable="false"
          onError={ctx.onImageError}
        />
      </div>
      {ctx.dish.is_rep_image && <div className="lab lab-sm muted pt-8">Representative image</div>}
    </div>
  );
}

function Summary({ ctx }) {
  if (!ctx.dish.summary) return null;
  return (
    <p className="body-serif clamp3 pt-12" style={{ margin: 0 }}>
      {ctx.dish.summary}
    </p>
  );
}

function Allergens({ ctx, block }) {
  return (
    <div className="pt-12">
      <span className={`tag-box${block.variant === 'emphasised' ? ' is-accent' : ''}`}>
        {allergenLine(ctx.dish.allergens)}
      </span>
    </div>
  );
}

/** What the search left out for this person's food rules. It never says a dish is safe. */
function Safety({ block }) {
  const lines = block.props?.lines || [];
  if (!lines.length) return null;
  return (
    <div className="safety rise">
      <div className="lab lab-sm accent">Your food rules</div>
      <ul className="safety-lines small">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </div>
  );
}

/** The number this person's goal is about, beside the price. Estimated, and says so. */
function Nutrition({ block }) {
  const { protein_g: protein, calories, confidence } = block.props || {};
  const protein_first = block.variant === 'protein';
  const value = protein_first ? protein : calories;
  if (value == null) return null;
  return (
    <div className="nutrition between pt-12">
      <div>
        <div className="bod-b" style={{ fontSize: 28 }}>
          {protein_first ? `${Math.round(value)} g` : `${Math.round(value)} kcal`}
        </div>
        <div className="lab lab-sm muted">{protein_first ? 'Protein' : 'Calories'}</div>
      </div>
      <div className="lab lab-sm muted" style={{ textAlign: 'right' }}>
        {protein_first
          ? calories != null && `in ${Math.round(calories)} kcal`
          : protein != null && `${Math.round(protein)} g protein`}
        {confidence && <div>Estimated</div>}
      </div>
    </div>
  );
}

function Reasons({ ctx, block }) {
  const order = block.props?.order;
  const rows = [...ctx.reasons];
  if (order?.length) {
    rows.sort((a, b) => {
      const rank = (row) => {
        const at = order.indexOf(REASON_KEYS[row.label] || row.label.toLowerCase());
        return at === -1 ? order.length : at;
      };
      return rank(a) - rank(b);
    });
  }
  if (!rows.length) return null;
  return (
    <div className="pt-16">
      {rows.map((r, i) => (
        <div className="reason" key={r.label}>
          <div className="lab lab-sm reason-label">{r.label}</div>
          <div className="grow">
            <div className="reason-score wide-only">
              <div className="bar is-accent">
                <span style={{ width: `${r.value}%`, animationDelay: `${300 + i * 120}ms` }} />
              </div>
              <span className="bod-b">{r.value}</span>
            </div>
            <div className="small">{r.text}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

/** What this person, and people with their taste, chose before. */
function History({ block }) {
  const lines = block.props?.lines || [];
  if (!lines.length) return null;
  return (
    <div className="pt-12">
      {lines.map((line) => (
        <div className="small accent" key={line}>
          {line}
        </div>
      ))}
    </div>
  );
}

/** How much the app knows about this person yet, so a generic pick isn't read as a claim. */
function Learning({ block }) {
  const text = block.props?.text;
  return text ? <p className="small muted pt-12">{text}</p> : null;
}

function WeightsBlock({ ctx }) {
  if (!ctx.blueprint?.agent_weights || !ctx.onWeights) return null;
  return (
    <div data-nodrag="1">
      <Weights
        weights={ctx.blueprint.agent_weights}
        onChange={ctx.onWeights}
        busy={ctx.busy}
        tasteUnset={ctx.blueprint.utility_breakdown?.u_taste == null}
      />
    </div>
  );
}

function RunnersBlock({ ctx, block }) {
  return (
    <div data-nodrag="1">
      <Runners
        candidates={ctx.blueprint?.top_candidates}
        winnerId={ctx.dish.dish_id}
        badges={block.props?.badges}
      />
    </div>
  );
}

export const BLOCKS = {
  match: Match,
  name: Name,
  place: Place,
  price: Price,
  photo: Photo,
  summary: Summary,
  allergens: Allergens,
  safety: Safety,
  nutrition: Nutrition,
  reasons: Reasons,
  history: History,
  learning: Learning,
  weights: WeightsBlock,
  runners: RunnersBlock,
};

/**
 * The layout to draw: the server's, or the fixed one. Kept in step with `ui/compose.py`'s
 * DEFAULT, so a reply without a layout — an older server, or one whose composer failed —
 * still draws the screen we had.
 */
const FIXED = [
  ['match', 'main'],
  ['name', 'main'],
  ['place', 'main'],
  ['price', 'main'],
  ['photo', 'side'],
  ['summary', 'main'],
  ['allergens', 'main'],
  ['reasons', 'side'],
  ['weights', 'main'],
  ['runners', 'band'],
];

export function layoutOf(blueprint) {
  const sent = blueprint?.layout;
  if (sent?.blocks?.length) return sent;
  return {
    blocks: FIXED.map(([id, slot]) => ({ id, type: id, slot, variant: 'default', props: {} })),
    why: [],
  };
}

/**
 * The blocks of one slot, in the order the layout gives. `o-N` carries that order through the
 * phone layout, where both columns are `display: contents` and flow as one.
 */
export function Slot({ layout, slot, ctx }) {
  return layout.blocks
    .map((block, index) => ({ block, order: index + 1 }))
    .filter(({ block }) => block.slot === slot && BLOCKS[block.type])
    .map(({ block, order }) => {
      const Block = BLOCKS[block.type];
      return (
        <div className={`o-${Math.min(order, 12)}`} key={block.id}>
          <Block ctx={ctx} block={block} />
        </div>
      );
    });
}
