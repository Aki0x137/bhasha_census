from kyc_bot.verification.ocr import (
    FakeDocProvider,
    _parse_card,
    mask_id,
    name_similarity,
)


def test_parse_card_extracts_name_and_id():
    md = "CENSUS DEMO\n\nName: Khushal Vyas\n\nID Number: 1234 5678 9012\n"
    r = _parse_card(md)
    assert r.name == "Khushal Vyas"
    assert r.id_number == "123456789012"


def test_parse_card_missing_fields_is_safe():
    r = _parse_card("some text with no labelled fields")
    assert r.name == "Unknown"
    assert r.id_number == "0000"


def test_mask_id_keeps_only_last_four():
    out = mask_id("999988887777")
    assert out.endswith("7777")
    assert "9999" not in out
    assert "8888" not in out


def test_mask_id_handles_spaces_and_short():
    assert mask_id("1234 5678 9012").endswith("9012")
    assert mask_id("12").endswith("12")


def test_name_similarity_identical_is_high():
    assert name_similarity("Ramesh Kumar", "ramesh kumar") > 0.9


def test_name_similarity_different_is_low():
    assert name_similarity("Ramesh Kumar", "Suresh Patel") < 0.7


def test_name_similarity_empty_is_zero():
    assert name_similarity("", "Ramesh") == 0.0


async def test_fake_provider_returns_sample():
    result = await FakeDocProvider().digitize(b"fake-bytes")
    assert result.name == "Ramesh Kumar"
    assert result.id_number
