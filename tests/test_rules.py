import pytest

from hadouken_zone.models import Offer
from hadouken_zone.rules import detect_platform, is_excluded, rejection_reason


@pytest.mark.parametrize("text, expected", [
    ("God of War Ragnarök PS5", "PS5"),
    ("Astro Bot - PlayStation 5", "PS5"),
    ("Mario Kart 8 Deluxe (Nintendo Switch)", "Nintendo Switch"),
    ("Zelda Tears of the Kingdom Switch", "Nintendo Switch"),
    ("Mario Kart World (Nintendo Switch 2)", None),
    ("Hogwarts Legacy PS5 / Nintendo Switch", None),
    ("FIFA PS4", None),
    ("Halo Xbox Series X", None),
])
def test_detect_platform(text, expected):
    assert detect_platform(text) == expected


def test_switch_2_can_be_enabled():
    assert detect_platform("Mario Kart World Nintendo Switch 2", include_switch_2=True) == "Nintendo Switch"


@pytest.mark.parametrize("title, excluded", [
    ("Sony Mando DualSense PS5", True),
    ("Auriculares gaming PS5", True),
    ("Consola PlayStation 5 Slim", True),
    ("Nintendo Switch Online 12 meses", True),
    ("Juego para consola Nintendo Switch: Kirby", False),
    ("God of War Ragnarök - Edición Estándar PS5", False),
])
def test_is_excluded(title, excluded):
    assert is_excluded(title) is excluded


def make(**kw):
    base = dict(asin="B0TSTPS501", title="Astro Bot PS5", price=35.0, previous_price=70.0)
    base.update(kw)
    return Offer(**base)


def test_valid_offer(settings):
    offer = make()
    assert rejection_reason(offer, settings) is None
    assert offer.platform == "PS5"


def test_platform_from_extra_text(settings):
    offer = make(title="Astro Bot", platform_text="Plataforma : PlayStation 5")
    assert rejection_reason(offer, settings) is None


@pytest.mark.parametrize("kw, motivo", [
    (dict(previous_price=40.0), "descuento insuficiente"),        # 12 %
    (dict(previous_price=None), "sin precio anterior"),
    (dict(previous_price=30.0), "sin precio anterior"),           # anterior < actual
    (dict(price=0), "precio actual"),
    (dict(price=3.0, previous_price=70.0), "descuento incoherente"),  # 96 %
    (dict(price=100.0, previous_price=999.0), "referencia incoherente"),
    (dict(available=False), "no disponible"),
    (dict(title="Mando DualSense PS5"), "no es un videojuego"),
    (dict(title="Halo Xbox"), "plataforma"),
])
def test_rejections(settings, kw, motivo):
    assert motivo in rejection_reason(make(**kw), settings)


def test_exactly_20_percent_is_accepted(settings):
    assert rejection_reason(make(price=40.0, previous_price=50.0), settings) is None


def test_default_minimum_is_15_percent(settings):
    assert settings.min_discount_percent == 15
    assert rejection_reason(make(price=42.5, previous_price=50.0), settings) is None      # 15 %
    assert "insuficiente" in rejection_reason(make(price=43.0, previous_price=50.0), settings)  # 14 %
