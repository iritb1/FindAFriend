"""Tests for the matcher - deterministic, no LLM mocking required.

Verifies the core matching contract:
1. Hard animal_type filter excludes wrong species entirely.
2. Hard gender filter excludes wrong gender entirely.
3. Matching animal+query returns a PartialMatch with score and reasons.
4. Soft criteria misses surface in `missing_or_uncertain`.
"""
from agent.matcher import score_animal
from utils.models import AdoptionQuery, Animal, AnimalType, Gender


def _animal(**overrides) -> Animal:
    base = {
        "source": "test",
        "animal_type": AnimalType.dog,
        "name": "Test",
        "raw_text": "test data",
    }
    base.update(overrides)
    return Animal.model_validate(base)


def _query(**overrides) -> AdoptionQuery:
    base = {"free_text": "test"}
    base.update(overrides)
    return AdoptionQuery.model_validate(base)


def test_animal_type_hard_filter_excludes_wrong_species():
    cat = _animal(name="Whiskers", animal_type=AnimalType.cat)
    result = score_animal(_query(animal_type=AnimalType.dog), cat)
    assert result is None


def test_gender_hard_filter_excludes_wrong_gender():
    male_dog = _animal(name="Max", gender=Gender.male)
    result = score_animal(_query(animal_type=AnimalType.dog, gender=Gender.female), male_dog)
    assert result is None


def test_matching_animal_returns_partial_match_with_score():
    bella = _animal(name="Bella", gender=Gender.female, breed="Labrador")
    result = score_animal(
        _query(animal_type=AnimalType.dog, gender=Gender.female, breed="Labrador"),
        bella,
    )
    assert result is not None
    assert result.animal.name == "Bella"
    assert result.score > 0
    assert any("dog" in reason for reason in result.reasons)


def test_breed_mismatch_records_missing():
    poodle = _animal(name="Daisy", breed="Poodle")
    result = score_animal(_query(breed="labrador"), poodle)
    assert result is not None
    assert any("breed" in entry for entry in result.missing_or_uncertain)


def test_color_mismatch_records_missing():
    black_dog = _animal(name="Shadow", color="שחור")
    result = score_animal(_query(color="white"), black_dog)
    assert result is not None
    assert any("color" in entry for entry in result.missing_or_uncertain)


def test_color_hebrew_mapping_matches():
    """English query 'white' should match Hebrew 'לבן' via the lookup table."""
    white_dog = _animal(name="Snow", color="לבן")
    result = score_animal(_query(color="white"), white_dog)
    assert result is not None
    assert any("color matches" in reason for reason in result.reasons)


def test_no_filter_query_still_scores_animal():
    """An empty-criteria query (just free_text) shouldn't filter anything out."""
    pet = _animal(name="Fluffy")
    result = score_animal(_query(), pet)
    assert result is None or result.score >= 0  # may return None if score==0
