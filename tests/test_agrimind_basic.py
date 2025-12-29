import importlib.util
import os
import sys


def _load_agrimind_module():
    # Import from path because folder name contains a space: "machine learning"
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "machine learning", "agrimind.py")
    spec = importlib.util.spec_from_file_location("agrimind", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_normalize_basic():
    m = _load_agrimind_module()
    assert m._normalize("Dâu_tây / BỆNH") == "dau tay benh"


def test_symptom_patterns_add_canonical_when_in_lexicon():
    m = _load_agrimind_module()
    q_norm = m._normalize("Con vật nhà tôi bị đau bụng và bỏ ăn")
    symptom_list = ["đau bụng", "bỏ ăn", "sốt"]
    found = m._extract_symptoms(q_norm, symptom_list)
    assert "đau bụng" in found
    assert "bỏ ăn" in found


def test_indexed_match_runs():
    m = _load_agrimind_module()

    # Minimal KB
    e1 = m.KBEntry(
        id="t1",
        domain="livestock",
        specie="heo",
        season="bat_ky",
        disease="tiêu chảy",
        symptoms=("tiêu chảy", "bỏ ăn"),
        causes=("vi khuẩn",),
        advice=("bù nước",),
        examples=("heo tiêu chảy",),
        safety_urgent=False,
        safety_notes=(),
    )
    e2 = m.KBEntry(
        id="t2",
        domain="crop",
        specie="lúa",
        season="mua",
        disease="đạo ôn",
        symptoms=("đốm lá",),
        causes=("nấm",),
        advice=("phun thuốc",),
        examples=("lúa bị đốm lá",),
        safety_urgent=False,
        safety_notes=(),
    )
    entries = [e1, e2]
    lex = m._build_lexicons(entries)
    index = m._build_kb_index(entries)

    extracted = m.extract_entities("Heo bị tiêu chảy bỏ ăn", entries, lex)
    best, conf = m.match_kb_indexed(extracted, entries, index)
    assert best is not None
    assert best.id == "t1"
    assert conf >= 0.1
