import { useEffect } from 'react';

export default function RecipeModal({ recipe, dish, open, onClose }) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  if (!recipe) return (
    <div className="recipe-modal" id="recipe-modal">
      <div className="recipe-modal-backdrop" id="recipe-modal-backdrop"></div>
      <div className="recipe-modal-content" id="recipe-modal-content"></div>
    </div>
  );

  const totalCost = (recipe.grocery_list || []).reduce((s, g) => s + (g.est_cost || 0), 0);

  return (
    <div className={`recipe-modal ${open ? 'open' : ''}`} id="recipe-modal">
      <div className="recipe-modal-backdrop" id="recipe-modal-backdrop" onClick={onClose}></div>
      <div className="recipe-modal-content" id="recipe-modal-content">
        <div className="recipe-header">
          <div className="recipe-header-top">
            <h2>🍽️ {dish?.name || 'Recipe'}</h2>
            <button className="recipe-close" id="recipe-close-btn" aria-label="Close recipe" onClick={onClose}>✕</button>
          </div>
          <div className="recipe-meta-row">
            <span className="recipe-meta-pill">⏱ Prep: {recipe.prep_time || '—'}</span>
            <span className="recipe-meta-pill">🔥 Cook: {recipe.cook_time || '—'}</span>
            <span className="recipe-meta-pill">🍽 Serves: {recipe.servings || '—'}</span>
            <span className={`recipe-meta-pill difficulty-${(recipe.difficulty || '').toLowerCase()}`}>{recipe.difficulty || '—'}</span>
          </div>
        </div>
        <div className="recipe-body">
          <h3>📋 Steps</h3>
          <ol className="recipe-steps">
            {(recipe.steps || []).map((s, i) => <li key={i}>{s}</li>)}
          </ol>
          <h3>🛒 Grocery List <span className="grocery-total">Est. Total: Rs. {totalCost}</span></h3>
          <div className="grocery-grid">
            {(recipe.grocery_list || []).map((g, i) => (
              <div key={i} className="grocery-item">
                <span className="grocery-name">{g.item}</span>
                <span className="grocery-qty">{g.qty}</span>
                <span className="grocery-cost">Rs. {g.est_cost}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
