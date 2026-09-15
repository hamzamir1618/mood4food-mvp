# Attributions

Mood4Food uses third-party data under open licences. This file records what is used, where it comes from, which licence covers it, and what each licence asks of us.

## Open Food Facts

- **What we use:** the protein and calorie estimates in the handoff dataset (`handoff_output/mood4food_dishes.csv`) were computed from ingredient values taken from Open Food Facts — 76 of the 82 ingredients in the sourcing project's `ingredient_nutrition_reference.csv`. The app's own dataset (`data/dishes_v2.csv`) no longer uses them: about half matched a different food entirely, so its nutrition comes from USDA FoodData Central instead (below).
- **Licence:** the database is available under the [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1.0/), and its individual contents under the [Database Contents License (DbCL) 1.0](https://opendatacommons.org/licenses/dbcl/1.0/). No Open Food Facts product images are used.
- **What it asks of us:** name the licence and attribute authorship to Open Food Facts with a link to https://openfoodfacts.org. Derivative databases must be shared under the same terms.
- **Credit:**
  > Contains information from Open Food Facts (https://openfoodfacts.org), which is made available here under the Open Database License (ODbL).

## USDA FoodData Central

- **What we use:** nutrition per 100 g (calories, protein, fat and carbohydrate) for all 116 ingredients the pipeline can attach to a dish, from the SR Legacy dataset. `data/reference/ingredient_nutrition.csv` records the FDC id and exact USDA description behind every value. The earlier handoff dataset also used USDA values for five ingredients: chicken, butter, rocket leaves, olive oil and lamb fat.
- **Licence:** public domain, published under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/). Attribution is not legally required; USDA asks to be listed as the source.
- **Credit:**
  > U.S. Department of Agriculture, Agricultural Research Service. FoodData Central. fdc.nal.usda.gov.

The handoff dataset's value for **pulao** is recorded only as "Standard reference cooked pulao", with no source named. The app's dataset does not use it: pulao is treated as rice, with USDA values.

## OpenStreetMap

- **What we use:** restaurant coordinates in the dataset were geocoded through Nominatim from each restaurant's name and sector, so they are approximate (see `handoff_output/HANDOFF_NOTES.md`). Distances shown in the app are computed from them. The optional `RESTAURANT_PROVIDER=osm` mode also queries the Overpass API live.
- **Licence:** [Open Database License (ODbL) 1.0](https://www.openstreetmap.org/copyright).
- **What it asks of us:** credit OpenStreetMap and make clear that the data is available under the ODbL, linking to https://www.openstreetmap.org/copyright. Applications that use a geocoder built on OpenStreetMap data must credit OpenStreetMap.
- **Credit:**
  > Location data © OpenStreetMap contributors, available under the Open Database License (https://www.openstreetmap.org/copyright).

## Unsplash

- **What we use:** stock photographs, hotlinked from images.unsplash.com, shown as placeholders when a dish has no photo of its own (`tier_1/symbolic_anchoring.py`). The app labels each one "Representative image".
- **Licence:** the [Unsplash License](https://unsplash.com/license), which allows free use without attribution.

## Open-Meteo

- **What we use:** the current temperature in Islamabad, fetched at most every 30 minutes, for the "context" term of the decision core (`tier_2/context.py`). A hot day favours lighter dishes and a cold one soups and curries.
- **Terms:** free for non-commercial use with no API key, under 10,000 calls a day (https://open-meteo.com/en/terms). A deployment with subscriptions or advertising would need a commercial plan.
- **Licence:** the data is provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Credit:**
  > Weather data by Open-Meteo.com (https://open-meteo.com), CC BY 4.0.

## Menu data

Dish names and prices come from restaurants' own websites and from human-reviewed OCR of menu photos. The sourcing method and compliance checks are recorded in `handoff_output/SOURCING_COMPLIANCE_LOG.md`.

## Open obligations

- **In-app credit — required before deployment.** The app shows nutrition estimates and restaurant distances derived from the sources above, but does not yet credit them anywhere. Add a footer or About line such as:
  > Nutrition estimates use data from Open Food Facts (ODbL) and USDA FoodData Central. Location data © OpenStreetMap contributors (ODbL). Weather data by Open-Meteo.com (CC BY 4.0).

  with links to https://openfoodfacts.org, https://www.openstreetmap.org/copyright and https://open-meteo.com.
- **Publishing the dataset.** This repository is public, and the datasets are kept out of it: `handoff_output/`, `data/` and `data_review/` are git-ignored. Both `data/dishes_v2.csv` and `handoff_output/mood4food_dishes.csv` are derivative databases — both contain coordinates derived from OpenStreetMap, and the handoff file also contains nutrition values derived from Open Food Facts. ODbL's share-alike terms apply to a derivative database that is publicly used, so publishing either one means releasing it under ODbL 1.0 with the credits above. A publicly deployed app built on it may also carry obligations. Read ODbL sections 4.4 (share-alike) and 4.6 (access to derivative databases) before either happens.
