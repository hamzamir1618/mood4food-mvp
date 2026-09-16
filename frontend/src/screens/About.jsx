/**
 * Where the numbers come from. ATTRIBUTIONS.md records this as required before
 * deployment: Open Food Facts and OpenStreetMap are ODbL, Open-Meteo is CC BY 4.0,
 * and USDA asks to be named. The wording follows that file.
 */
export default function About({ onClose }) {
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className="sheet" role="dialog" aria-label="Where the data comes from">
        <div className="between">
          <div className="lab accent">Where the data comes from</div>
          <button className="lab lab-sm muted" onClick={onClose}>
            Close ✕
          </button>
        </div>

        <div className="h3 pt-12">Menus</div>
        <p className="text" style={{ margin: '6px 0 0' }}>
          Dish names and prices come from the restaurants' own websites and from menu photos
          read by hand. Prices change, and a restaurant's own menu is the last word.
        </p>

        <div className="h3 pt-16">Nutrition</div>
        <p className="text" style={{ margin: '6px 0 0' }}>
          Calories and protein are estimated from a dish's typical ingredients, not measured.
          Ingredient values come from{' '}
          <a href="https://openfoodfacts.org" target="_blank" rel="noreferrer">Open Food Facts</a>{' '}
          (ODbL) and{' '}
          <a href="https://fdc.nal.usda.gov" target="_blank" rel="noreferrer">
            USDA FoodData Central
          </a>
          . Allergens are worked out the same way, so treat them as a guide and check with the
          restaurant if it matters.
        </p>

        <div className="h3 pt-16">Distances</div>
        <p className="text" style={{ margin: '6px 0 0' }}>
          Location data ©{' '}
          <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
            OpenStreetMap contributors
          </a>
          , available under the Open Database License. Restaurant coordinates are geocoded and
          approximate, and distances are measured in a straight line.
        </p>

        <div className="h3 pt-16">Weather</div>
        <p className="text" style={{ margin: '6px 0 0' }}>
          Weather data by{' '}
          <a href="https://open-meteo.com" target="_blank" rel="noreferrer">Open-Meteo.com</a>,
          CC BY 4.0. A hot day nudges the pick towards lighter dishes.
        </p>

        <div className="h3 pt-16">Photographs</div>
        <p className="text" style={{ margin: '6px 0 0' }}>
          Dishes without a photo of their own show a stock photograph from Unsplash, labelled
          "Representative image". It shows the kind of dish, not the plate you'll be served.
        </p>

        <button className="btn btn-line" style={{ marginTop: 20 }} onClick={onClose}>
          <span className="lab">Done</span>
        </button>
      </div>
    </>
  );
}
