import LogoMark from './components/LogoMark.jsx';
import { CardFrame, SectionDivider, CornerFlourish } from './components/ornaments/index.js';

/* ── Design-system tokens (inline so this page has zero dependency on style.css) ── */
const T = {
  bgDeep: '#1B1411', bgElev: '#241C17', bgRec: '#130F0C', bgWash: '#2A201A',
  txPri: '#F0EDE8', txSec: '#B8AFA5', txTer: '#7A7168', txOnGold: '#1B1411',
  gold: '#C9A84C', goldLt: '#DFC478', goldMut: '#8A7A4A',
  success: '#5AAF6A', warning: '#D4A023', error: '#E05858',
};

const CUISINES = [
  { key: 'desi_traditional',   label: 'Desi',          color: '#D4763C', font: 'Cinzel',             weight: 700, dish: 'Chicken Karahi',           desc: 'Aromatic karahi with tender chicken, tomato gravy, green chillies', price: 850 },
  { key: 'chinese_asian',      label: 'Chinese/Asian',  color: '#E05858', font: 'Noto Serif Variable', weight: 600, dish: 'Spicy & Sour Tom Yum Gai',desc: 'Thai sour broth with chicken, lemongrass, galangal',             price: 1075 },
  { key: 'middle_eastern',     label: 'Middle Eastern', color: '#4AA882', font: 'Cinzel Decorative',  weight: 400, dish: 'Baba Ganoush',              desc: 'Smoky roasted aubergine dip with tahini and warm pita',          price: 550 },
  { key: 'continental_upscale',label: 'Continental',    color: '#9B88C8', font: 'Playfair Display Variable', weight: 700, dish: 'Caeser Salad',       desc: 'Romaine, parmesan, croutons, anchovy dressing',                  price: 780 },
  { key: 'fast_food',          label: 'Fast Food',      color: '#D4A023', font: 'Bebas Neue',         weight: 400, dish: 'AFGHAN CHICKEN TIKKA BURGER', desc: 'Grilled tikka patty with fresh lettuce and special sauce',     price: 330, upper: true },
  { key: 'cafe_bakery',        label: 'Café & Bakery',  color: '#C47A5A', font: 'Fraunces Variable',  weight: 500, dish: 'Cappuccino',                desc: 'Double-shot espresso with velvety steamed milk foam',            price: 480 },
  { key: 'pizza',              label: 'Pizza',          color: '#D4624E', font: 'Bebas Neue',         weight: 400, dish: 'CROWN CRUST PIZZA',          desc: 'Signature stuffed-crust with premium toppings',                  price: 1200, upper: true },
  { key: 'beverages',          label: 'Beverages',      color: '#4A94B8', font: 'Fraunces Variable',  weight: 400, dish: 'Kiwi Delight',               desc: 'Fresh kiwi blended with crushed ice and mint',                   price: 350 },
  { key: 'other',              label: 'Other',          color: '#8B8178', font: 'Source Serif 4 Variable', weight: 600, dish: 'Red Lentil Soup',       desc: 'Classic Turkish-style lentil soup with lemon wedge',             price: 420 },
];

const SURFACES = [
  { token: '--bg-deep',      hex: T.bgDeep, label: 'bg-deep',      note: 'Primary page background' },
  { token: '--bg-elevated',  hex: T.bgElev, label: 'bg-elevated',  note: 'Cards, modals' },
  { token: '--bg-recessed',  hex: T.bgRec,  label: 'bg-recessed',  note: 'Input wells, sidebar' },
  { token: '--bg-warm-wash', hex: T.bgWash, label: 'bg-warm-wash', note: 'Hover, active rows' },
];

const TEXT_TIERS = [
  { token: '--text-primary',   hex: T.txPri, label: 'Primary',   ratio: '15.6:1', grade: 'AAA' },
  { token: '--text-secondary', hex: T.txSec, label: 'Secondary', ratio: '8.4:1',  grade: 'AAA' },
  { token: '--text-tertiary',  hex: T.txTer, label: 'Tertiary',  ratio: '3.8:1',  grade: 'AA-lg' },
];

/* ── Shared inline styles ── */
const page = { background: T.bgDeep, color: T.txPri, fontFamily: "'Source Serif 4 Variable','Source Serif 4',Georgia,serif", minHeight: '100vh', padding: '40px 24px' };
const container = { maxWidth: 900, margin: '0 auto' };
const sectionTitle = { fontFamily: "'Outfit Variable','Outfit',sans-serif", fontWeight: 700, fontSize: 14, color: T.gold, letterSpacing: 3, textTransform: 'uppercase', marginBottom: 6 };
const sectionSub = { fontSize: 13, color: T.txSec, marginBottom: 20, lineHeight: 1.6 };
const hr = { border: 'none', borderTop: `1px solid ${T.goldMut}`, opacity: 0.3, margin: '40px 0' };

export default function StyleGuide() {
  return (
    <div style={page}>
      <div style={container}>

        {/* ═══════════════════════════════════════════════════════
            HEADER
            ═══════════════════════════════════════════════════════ */}
        <header style={{ textAlign: 'center', marginBottom: 48 }}>
          <LogoMark size={64} />
          <h1 style={{ fontFamily: "'Outfit Variable','Outfit',sans-serif", fontWeight: 700, fontSize: 32, margin: '12px 0 4px', letterSpacing: 2 }}>
            Mood4Food
          </h1>
          <p style={{ fontSize: 12, color: T.txTer, letterSpacing: 4, textTransform: 'uppercase' }}>
            Design System Style Guide
          </p>
          <p style={{ fontSize: 13, color: T.txSec, marginTop: 12 }}>
            Static reference page — all elements rendered with real self-hosted fonts and SVG components
          </p>
        </header>

        {/* ═══════════════════════════════════════════════════════
            1. LOGO
            ═══════════════════════════════════════════════════════ */}
        <section>
          <p style={sectionTitle}>1 · Logo</p>
          <p style={sectionSub}>Wax-seal compass crest — mark-only and full lockup, on light and dark</p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            {/* Mark on dark */}
            <div style={{ background: T.bgElev, borderRadius: 12, padding: 24, textAlign: 'center', border: `1px solid ${T.goldMut}30` }}>
              <LogoMark size={80} />
              <div style={{ fontSize: 11, color: T.txTer, marginTop: 8 }}>Mark · dark background</div>
            </div>
            {/* Mark on light */}
            <div style={{ background: '#F0EDE8', borderRadius: 12, padding: 24, textAlign: 'center', color: T.bgDeep }}>
              <LogoMark size={80} />
              <div style={{ fontSize: 11, color: '#7A7168', marginTop: 8 }}>Mark · light background</div>
            </div>
          </div>

          {/* Full lockup */}
          <div style={{ background: T.bgElev, borderRadius: 12, padding: '24px 28px', border: `1px solid ${T.goldMut}30` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
              <LogoMark size={56} />
              <div>
                <div style={{ fontFamily: "'Outfit Variable','Outfit',sans-serif", fontSize: 32, fontWeight: 700, letterSpacing: 3, lineHeight: 1 }}>
                  <span>MOOD</span>
                  <span style={{ fontWeight: 300, margin: '0 4px' }}>4</span>
                  <span>FOOD</span>
                </div>
                <div style={{ height: 1, background: T.goldMut, opacity: 0.3, margin: '6px 0' }} />
                <div style={{ fontSize: 10, color: T.txTer, letterSpacing: 4 }}>CURATED DINING DISCOVERY</div>
              </div>
            </div>
          </div>

          {/* Favicon sizes */}
          <div style={{ display: 'flex', gap: 20, alignItems: 'end', marginTop: 16 }}>
            {[16, 24, 32, 44].map(s => (
              <div key={s} style={{ textAlign: 'center' }}>
                <LogoMark size={s} />
                <div style={{ fontSize: 10, color: T.txTer, marginTop: 4 }}>{s}px</div>
              </div>
            ))}
          </div>
        </section>

        <hr style={hr} />

        {/* ═══════════════════════════════════════════════════════
            2. COLOR PALETTE
            ═══════════════════════════════════════════════════════ */}
        <section>
          <p style={sectionTitle}>2 · Color Palette</p>
          <p style={sectionSub}>Espresso-ink base · Gold/brass accent · 9 cuisine accents · Semantic status</p>

          {/* Surfaces */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 6, fontWeight: 600 }}>Surfaces</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 20 }}>
            {SURFACES.map(s => (
              <div key={s.token} style={{ background: s.hex, borderRadius: 8, padding: '16px 12px', border: `1px solid ${T.goldMut}30` }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: T.txPri }}>{s.label}</div>
                <div style={{ fontSize: 11, fontFamily: 'monospace', color: T.txSec, marginTop: 2 }}>{s.hex}</div>
                <div style={{ fontSize: 10, color: T.txTer, marginTop: 2 }}>{s.note}</div>
              </div>
            ))}
          </div>

          {/* Text tiers */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 6, fontWeight: 600 }}>Text Tiers</div>
          <div style={{ background: T.bgDeep, borderRadius: 8, padding: 16, marginBottom: 20, border: `1px solid ${T.goldMut}20` }}>
            {TEXT_TIERS.map(t => (
              <div key={t.token} style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 6 }}>
                <span style={{ color: t.hex, fontSize: 18, fontWeight: 600, minWidth: 200 }}>{t.label} text sample</span>
                <span style={{ fontFamily: 'monospace', fontSize: 11, color: T.txTer }}>{t.hex}</span>
                <span style={{ fontSize: 10, color: t.grade === 'AAA' ? T.success : T.warning, fontWeight: 700 }}>{t.ratio} {t.grade}</span>
              </div>
            ))}
          </div>

          {/* Gold */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 6, fontWeight: 600 }}>Gold / Brass Accent</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 20 }}>
            {[
              { hex: T.gold,   label: 'gold',       note: 'Borders, highlights' },
              { hex: T.goldLt, label: 'gold-light',  note: 'Hover / glow' },
              { hex: T.goldMut,label: 'gold-muted',  note: 'Decorative only' },
            ].map(g => (
              <div key={g.hex} style={{ display: 'flex', gap: 10, alignItems: 'center', background: T.bgElev, borderRadius: 8, padding: '10px 12px', border: `1px solid ${T.goldMut}30` }}>
                <div style={{ width: 36, height: 36, borderRadius: '50%', background: g.hex, flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: T.txPri }}>{g.label}</div>
                  <div style={{ fontSize: 10, fontFamily: 'monospace', color: T.txSec }}>{g.hex}</div>
                  <div style={{ fontSize: 10, color: T.txTer }}>{g.note}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Cuisine accents */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 6, fontWeight: 600 }}>Cuisine Accents</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 20 }}>
            {CUISINES.map(c => (
              <div key={c.key} style={{ display: 'flex', gap: 10, alignItems: 'center', background: T.bgElev, borderRadius: 8, padding: '8px 12px', border: `1px solid ${T.goldMut}20` }}>
                <div style={{ width: 20, height: 20, borderRadius: '50%', background: c.color, flexShrink: 0, border: `2px solid ${T.goldMut}50` }} />
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: c.color }}>{c.label}</div>
                  <div style={{ fontSize: 10, fontFamily: 'monospace', color: T.txTer }}>{c.color}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Status */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 6, fontWeight: 600 }}>Semantic / Status</div>
          <div style={{ display: 'flex', gap: 12 }}>
            {[
              { hex: T.success, label: 'Success' },
              { hex: T.warning, label: 'Warning' },
              { hex: T.error,   label: 'Error' },
            ].map(s => (
              <div key={s.hex} style={{ display: 'flex', alignItems: 'center', gap: 8, background: T.bgElev, borderRadius: 8, padding: '8px 14px', border: `1px solid ${T.goldMut}20` }}>
                <div style={{ width: 14, height: 14, borderRadius: '50%', background: s.hex }} />
                <span style={{ fontSize: 12, color: s.hex, fontWeight: 600 }}>{s.label}</span>
                <span style={{ fontSize: 10, fontFamily: 'monospace', color: T.txTer }}>{s.hex}</span>
              </div>
            ))}
          </div>
        </section>

        <hr style={hr} />

        {/* ═══════════════════════════════════════════════════════
            3. TYPOGRAPHY PAIRINGS
            ═══════════════════════════════════════════════════════ */}
        <section>
          <p style={sectionTitle}>3 · Typography Pairings</p>
          <p style={sectionSub}>
            Tier 1 workhorse (Source Serif 4) for functional text · Tier 2 cuisine display font for dish names · Real dishes from dataset
          </p>

          {/* Workhorse specimen */}
          <div style={{ background: T.bgElev, borderRadius: 10, padding: '16px 20px', marginBottom: 16, border: `1px solid ${T.goldMut}20` }}>
            <div style={{ fontSize: 11, color: T.txTer, marginBottom: 8 }}>TIER 1 · Source Serif 4 Variable · all functional text</div>
            <div style={{ fontWeight: 200, fontSize: 14, marginBottom: 2 }}>Weight 200 — Light caption text</div>
            <div style={{ fontWeight: 400, fontSize: 15, marginBottom: 2 }}>Weight 400 — Body copy and descriptions</div>
            <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 2 }}>Weight 600 — Subtitles and emphasis</div>
            <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 2 }}>Weight 700 — Section headings</div>
            <div style={{ fontWeight: 900, fontSize: 20 }}>Weight 900 — Black display</div>
          </div>

          {/* Per-cuisine pairings */}
          <div style={{ display: 'grid', gap: 10 }}>
            {CUISINES.map(c => (
              <div key={c.key} style={{ background: T.bgElev, borderRadius: 10, padding: '14px 18px', borderLeft: `3px solid ${c.color}`, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 8 }}>
                <div style={{ flex: 1, minWidth: 250 }}>
                  <div style={{ fontSize: 10, color: T.txTer, marginBottom: 2 }}>
                    {c.font} {c.weight} · {c.key}
                  </div>
                  <div style={{ fontFamily: `'${c.font}',serif`, fontWeight: c.weight, fontSize: c.upper ? 24 : 21, color: T.txPri, letterSpacing: c.upper ? 1.5 : 0, lineHeight: 1.2 }}>
                    {c.dish}
                  </div>
                  <div style={{ fontSize: 13, color: T.txSec, marginTop: 4, fontWeight: 400 }}>{c.desc}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ color: T.gold, fontWeight: 600, fontSize: 15 }}>Rs. {c.price.toLocaleString()}</span>
                  <div>
                    <span style={{ background: c.color, color: T.bgDeep, padding: '2px 8px', borderRadius: 12, fontSize: 9, fontWeight: 700 }}>{c.label.toUpperCase()}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <hr style={hr} />

        {/* ═══════════════════════════════════════════════════════
            4. ORNAMENTAL ELEMENTS
            ═══════════════════════════════════════════════════════ */}
        <section>
          <p style={sectionTitle}>4 · Ornamental Elements</p>
          <p style={sectionSub}>SVG corner flourishes · Section dividers · Background textures · Filigree edges — zero raster images</p>

          {/* Corner flourishes */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 6, fontWeight: 600 }}>Corner Flourishes</div>
          <div style={{ display: 'flex', gap: 20, alignItems: 'end', marginBottom: 20, flexWrap: 'wrap' }}>
            {[24, 32, 40, 52].map(s => (
              <div key={s} style={{ textAlign: 'center' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: s * 0.8, color: T.gold }}>
                  <CornerFlourish size={s} position="tl" />
                  <CornerFlourish size={s} position="tr" />
                  <CornerFlourish size={s} position="bl" />
                  <CornerFlourish size={s} position="br" />
                </div>
                <div style={{ fontSize: 10, color: T.txTer, marginTop: 6 }}>{s}px</div>
              </div>
            ))}
          </div>

          {/* Dividers */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 6, fontWeight: 600 }}>Section Dividers</div>
          <div style={{ background: T.bgElev, borderRadius: 10, padding: '16px 20px', marginBottom: 20, color: T.gold }}>
            <div style={{ fontSize: 10, color: T.txTer, marginBottom: 4 }}>Diamond (default)</div>
            <SectionDivider variant="diamond" />
            <div style={{ fontSize: 10, color: T.txTer, marginBottom: 4, marginTop: 16 }}>Flourish</div>
            <SectionDivider variant="flourish" />
            <div style={{ fontSize: 10, color: T.txTer, marginBottom: 4, marginTop: 16 }}>Simple</div>
            <SectionDivider variant="simple" />
          </div>

          {/* Textures */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 6, fontWeight: 600 }}>Background Textures</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 20 }}>
            <div style={{ background: T.bgElev, borderRadius: 10, padding: 20, textAlign: 'center' }}>
              <div style={{ fontWeight: 600, fontSize: 13 }}>Plain</div>
              <div style={{ fontSize: 10, color: T.txTer }}>No texture</div>
            </div>
            <div className="ornament-texture-linen" style={{ background: T.bgElev, borderRadius: 10, padding: 20, textAlign: 'center' }}>
              <div style={{ fontWeight: 600, fontSize: 13, position: 'relative', zIndex: 2 }}>Linen</div>
              <div style={{ fontSize: 10, color: T.txTer, position: 'relative', zIndex: 2 }}>SVG feTurbulence</div>
            </div>
            <div className="ornament-texture-crosshatch" style={{ background: T.bgElev, borderRadius: 10, padding: 20, textAlign: 'center' }}>
              <div style={{ fontWeight: 600, fontSize: 13, position: 'relative', zIndex: 2 }}>Crosshatch</div>
              <div style={{ fontSize: 10, color: T.txTer, position: 'relative', zIndex: 2 }}>CSS gradients</div>
            </div>
          </div>

          {/* Filigree */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 6, fontWeight: 600 }}>Filigree Scallop Edge</div>
          <div className="ornament-filigree-edge" style={{ background: T.bgElev, borderRadius: 10, padding: '20px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>Repeating scallop arch in gold</div>
            <div style={{ fontSize: 10, color: T.txTer }}>SVG data URI · 24px repeating tile</div>
          </div>
        </section>

        <hr style={hr} />

        {/* ═══════════════════════════════════════════════════════
            5. UI COMPONENTS
            ═══════════════════════════════════════════════════════ */}
        <section>
          <p style={sectionTitle}>5 · UI Components</p>
          <p style={sectionSub}>Button, card, and input field styled in the design system</p>

          {/* Buttons */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 8, fontWeight: 600 }}>Buttons</div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
            {/* Primary (gold) */}
            <button style={{
              background: T.gold, color: T.bgDeep, border: 'none', borderRadius: 6,
              padding: '10px 24px', fontSize: 14, fontWeight: 700, cursor: 'pointer',
              fontFamily: "'Source Serif 4 Variable',Georgia,serif", letterSpacing: 0.5,
            }}>Discover Dishes</button>
            {/* Gold outline */}
            <button style={{
              background: 'transparent', color: T.gold, border: `1.5px solid ${T.gold}`,
              borderRadius: 6, padding: '10px 24px', fontSize: 14, fontWeight: 600,
              cursor: 'pointer', fontFamily: "'Source Serif 4 Variable',Georgia,serif",
            }}>Re-Roll ↻</button>
            {/* Ghost */}
            <button style={{
              background: T.bgWash, color: T.txSec, border: `1px solid ${T.goldMut}40`,
              borderRadius: 6, padding: '10px 24px', fontSize: 14, fontWeight: 500,
              cursor: 'pointer', fontFamily: "'Source Serif 4 Variable',Georgia,serif",
            }}>View Recipe</button>
            {/* Small cuisine pill */}
            <button style={{
              background: '#D4763C', color: T.bgDeep, border: 'none',
              borderRadius: 20, padding: '6px 16px', fontSize: 11, fontWeight: 700,
              cursor: 'pointer', fontFamily: "'Source Serif 4 Variable',Georgia,serif",
            }}>Desi Traditional</button>
          </div>

          {/* Input */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 8, fontWeight: 600 }}>Input Field</div>
          <div style={{ maxWidth: 420, marginBottom: 24 }}>
            <label style={{ fontSize: 12, color: T.txSec, display: 'block', marginBottom: 4 }}>What are you craving?</label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                placeholder="Something spicy under Rs. 800..."
                readOnly
                style={{
                  width: '100%', boxSizing: 'border-box',
                  background: T.bgRec, color: T.txPri, border: `1px solid ${T.goldMut}60`,
                  borderRadius: 6, padding: '12px 16px', fontSize: 15,
                  fontFamily: "'Source Serif 4 Variable',Georgia,serif",
                  outline: 'none',
                }}
              />
            </div>
            <div style={{ fontSize: 11, color: T.txTer, marginTop: 4 }}>
              bg-recessed background · gold-muted border · Source Serif 4 text
            </div>
          </div>

          {/* Full card with ornaments */}
          <div style={{ fontSize: 12, color: T.txTer, marginBottom: 8, fontWeight: 600 }}>Sample Card (with ornaments)</div>
          <div style={{ maxWidth: 440 }}>
            <CardFrame cornerSize={30} accentColor={T.goldMut}>
              <div className="ornament-filigree-edge" style={{ padding: '22px 20px' }}>
                <div style={{ position: 'relative', zIndex: 2 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontFamily: "'Playfair Display Variable',serif", fontWeight: 700, fontSize: 22, color: T.txPri }}>
                      Caeser Salad
                    </span>
                    <span style={{ background: '#9B88C8', color: T.bgDeep, padding: '2px 10px', borderRadius: 20, fontSize: 10, fontWeight: 700 }}>
                      CONTINENTAL
                    </span>
                  </div>

                  <div style={{ color: T.gold, margin: '6px 0' }}>
                    <SectionDivider variant="flourish" />
                  </div>

                  <p style={{ color: T.txSec, fontSize: 13.5, lineHeight: 1.7, margin: 0 }}>
                    Romaine lettuce, shaved parmesan, garlic croutons, and classic anchovy dressing. Served with artisan bread.
                  </p>

                  <div style={{ color: T.gold, margin: '6px 0' }}>
                    <SectionDivider variant="simple" />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: T.gold, fontWeight: 600, fontSize: 16 }}>Rs. 780</span>
                    <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
                      <span style={{ color: T.success }}>💪 72%</span>
                      <span style={{ color: T.warning }}>💰 88%</span>
                      <span style={{ color: T.error }}>😋 91%</span>
                    </div>
                  </div>

                  {/* Score bars */}
                  <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                    {[
                      { label: 'Health', pct: 72, color: T.success },
                      { label: 'Budget', pct: 88, color: T.warning },
                      { label: 'Taste',  pct: 91, color: T.error },
                    ].map(b => (
                      <div key={b.label} style={{ flex: 1 }}>
                        <div style={{ fontSize: 10, color: T.txTer, marginBottom: 3 }}>{b.label}</div>
                        <div style={{ height: 4, background: T.bgWash, borderRadius: 2, overflow: 'hidden' }}>
                          <div style={{ width: `${b.pct}%`, height: '100%', background: b.color, borderRadius: 2 }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardFrame>
          </div>
        </section>

        <hr style={hr} />

        {/* ═══════════════════════════════════════════════════════
            FOOTER
            ═══════════════════════════════════════════════════════ */}
        <footer style={{ textAlign: 'center', padding: '20px 0 40px', color: T.txTer, fontSize: 12 }}>
          <SectionDivider variant="diamond" />
          <div style={{ marginTop: 16 }}>
            Mood4Food Design System · Phase 1 Style Guide · For review before application
          </div>
        </footer>

      </div>
    </div>
  );
}
