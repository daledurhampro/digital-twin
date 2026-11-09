import json

import resources


def test_facts_loaded_from_json():
    with open("data/facts.json", encoding="utf-8") as f:
        expected = json.load(f)
    assert resources.facts == expected
    assert resources.facts["full_name"]
    assert resources.facts["name"]


def test_summary_loaded():
    with open("data/summary.txt", encoding="utf-8") as f:
        assert resources.summary == f.read()


def test_style_loaded():
    with open("data/style.txt", encoding="utf-8") as f:
        assert resources.style == f.read()


def test_pdf_text_extracted():
    assert isinstance(resources.linkedin, str)
    assert len(resources.linkedin) > 0
