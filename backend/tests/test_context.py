import re

import context
from resources import facts, style, summary


def test_names_come_from_facts():
    assert context.full_name == facts["full_name"]
    assert context.name == facts["name"]


def test_prompt_includes_identity_and_data():
    text = context.prompt()
    assert f"digital twin of {facts['full_name']}" in text
    assert f"who goes by {facts['name']}" in text
    assert summary in text
    assert style in text
    assert str(facts) in text


def test_prompt_includes_current_timestamp():
    text = context.prompt()
    assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text)


def test_prompt_includes_guardrails():
    text = context.prompt()
    assert "Do not invent or hallucinate" in text
    assert "jailbreak" in text
