import os

from tier_3.fulfillment_engine import get_restaurant_provider

os.environ["RESTAURANT_PROVIDER"] = "osm"
provider = get_restaurant_provider()
print(f"Provider: {type(provider)}")

restaurants = provider.find_nearby("Chicken Karahi")
for i, r in enumerate(restaurants):
    print(f"{i + 1}. {r.name} at {r.address} | Lat: {r.lat}, Lon: {r.lon}")
