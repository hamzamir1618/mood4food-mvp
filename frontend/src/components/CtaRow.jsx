export default function CtaRow({ onRecipe, onOrder }) {
  return (
    <div className="cta-row">
      <button className="cta-btn cta-recipe" id="cta-recipe" onClick={onRecipe}>🍽️ View Recipe</button>
      <button className="cta-btn cta-order" id="cta-order" onClick={onOrder}>🛵 Order Nearby</button>
    </div>
  );
}
