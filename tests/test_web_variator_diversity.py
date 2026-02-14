from skills.web_variator.variator_engine import VariatorEngine


def test_variator_generates_multiple_layouts():
    engine = VariatorEngine()
    variations = engine.generate_variations("Fashion", suggested_layout="editorial_stack")
    layouts = {v.get("layout") for v in variations}

    assert len(variations) >= 4
    assert "editorial_stack" in layouts
    assert len(layouts) >= 3


def test_variator_prefers_hint_when_balanced(monkeypatch):
    monkeypatch.setenv("WEB_DIVERSITY_MODE", "balanced")
    engine = VariatorEngine()
    variations = engine.generate_variations("Tech", suggested_layout="split_showcase")
    selected = engine.select_best_variation(variations, "Tech", suggested_layout="split_showcase")

    assert selected.get("layout") == "split_showcase"
    assert selected.get("theme") == "NeoTech"


def test_variator_returns_valid_choice_when_aggressive(monkeypatch):
    monkeypatch.setenv("WEB_DIVERSITY_MODE", "aggressive")
    engine = VariatorEngine()
    variations = engine.generate_variations("Cafe", suggested_layout="hero_centered")
    selected = engine.select_best_variation(variations, "Cafe", suggested_layout="hero_centered")

    assert selected in variations
    assert selected.get("layout") in {"hero_centered", "split_showcase", "editorial_stack", "catalog_grid"}
