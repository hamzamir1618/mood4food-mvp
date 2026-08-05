from tier_3.fulfillment_engine import generate_foodpanda_link, generate_whatsapp_link


def test_generate_foodpanda_link_basic():
    link = generate_foodpanda_link("KFC", "Zinger")
    assert link == "https://www.foodpanda.pk/search?q=KFC%20Zinger"


def test_generate_foodpanda_link_special_chars():
    link = generate_foodpanda_link("Biryani & Kebab House", "Spicy Chicken + Rice!")
    assert (
        link
        == "https://www.foodpanda.pk/search?q=Biryani%20%26%20Kebab%20House%20Spicy%20Chicken%20%2B%20Rice%21"
    )


def test_generate_whatsapp_link_basic():
    link = generate_whatsapp_link("923001234567", "Hello")
    assert link == "https://wa.me/923001234567?text=Hello"


def test_generate_whatsapp_link_special_chars():
    link = generate_whatsapp_link("+923001234567", "Hi, I'd like to order 2x Biryani & 1x Cola!")
    assert (
        link
        == "https://wa.me/+923001234567?text=Hi%2C%20I%27d%20like%20to%20order%202x%20Biryani%20%26%201x%20Cola%21"
    )
