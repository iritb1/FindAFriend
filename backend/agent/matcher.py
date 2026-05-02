import json
import re
from pathlib import Path

from utils.constants import (
    ENGLISH_TO_HEBREW_BREEDS,
    ENGLISH_TO_HEBREW_COLORS,
    HEBREW_MONTH_WORDS,
    HEBREW_TRAIT_KEYWORDS,
    HEBREW_YEAR_WORDS,
    IGNORED_WORDS,
)
from utils.models import AdoptionQuery, Animal, AnimalType, Gender, PartialMatch


ANIMALS_PATH = Path(__file__).resolve().parent.parent / "data" / "animals.json"


def load_animals(path: Path = ANIMALS_PATH) -> list[Animal]:
    """ Loads the scraped catalog """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return [Animal.model_validate(item) for item in data]


def normalize_text(value: str | None) -> str:
    """Lowercase + strip, with None tolerance.

    Args:
        value: A field value that may be missing.

    Returns:
        The stripped, lowercased string. Empty string if value is None/empty.
    """
    if not value:
        return ""

    return value.lower().strip()


def combined_animal_text(animal: Animal) -> str:
    """Concatenates every searchable field of an animal into one lowercase string.

    Used as the haystack for substring/keyword matching in breed/color/trait/
    free-text scoring functions.

    Args:
        animal: The animal whose fields to combine.

    Returns:
        String of name + type + gender + age +breed + color + description + raw_text.
        Empty fields are skipped.
    """
    parts = [
        animal.name,
        animal.animal_type.value if animal.animal_type else None,
        animal.gender.value if animal.gender else None,
        animal.age,
        animal.breed,
        animal.color,
        animal.description,
        animal.raw_text,
    ]

    return " ".join(str(part) for part in parts if part).lower()


def age_matches(query: AdoptionQuery, animal: Animal) -> tuple[bool, str | None]:
    """Tests whether the animal's age fits the query's age preference.

    Reads the Hebrew free-text animal.age field, extracts the numeric amount and the months/years unit, and
    compares against the requested bucket.

    Args:
        query: The adoption query (only age_preference is read).
        animal: The animal to score (only age is read).

    Returns:
        (True, None) if the age fits or no preference was set.
    """
    if not query.age_preference:
        return True, None

    pref = query.age_preference.lower()
    age = normalize_text(animal.age)

    if not age:
        return False, "age is missing"

    numbers = re.findall(r"\d+", age)
    amount = int(numbers[0]) if numbers else None

    is_months = any(word in age for word in HEBREW_MONTH_WORDS)
    is_years = any(word in age for word in HEBREW_YEAR_WORDS)

    if pref in {"puppy", "kitten", "baby"}:
        if is_months:
            return True, None

        return False, "not a baby/puppy/kitten"

    if pref == "young":
        if is_months:
            return True, None

        if is_years and amount is not None and amount <= 2:
            return True, None

        return False, "not young"

    if pref == "adult":
        if is_years and amount is not None and 2 <= amount <= 7:
            return True, None

        return False, "not adult"

    if pref == "senior":
        if is_years and amount is not None and amount >= 7:
            return True, None

        return False, "not senior"

    return True, None

def breed_matches(query_breed: str | None, animal: Animal) -> tuple[bool, str | None]:
    """Tests whether the animal's breed matches the requested breed.

    First tries direct substring match (English on English, or Hebrew on
    Hebrew). If that fails, looks the wanted breed up in
    ENGLISH_TO_HEBREW_BREEDS and tries each Hebrew alias.

    Args:
        query_breed: The breed the user asked for, or None.
        animal: The animal being scored.

    Returns:
        (True, None) on match or no preference.
        (False, "breed does not clearly match: X") otherwise.
    """
    if not query_breed:
        return True, None

    wanted = query_breed.lower().strip()
    animal_breed = normalize_text(animal.breed)
    animal_text = combined_animal_text(animal)

    if wanted in animal_breed or wanted in animal_text:
        return True, None

    hebrew_options = ENGLISH_TO_HEBREW_BREEDS.get(wanted, [])

    for option in hebrew_options:
        if option in animal_breed or option in animal_text:
            return True, None

    return False, f"breed does not clearly match: {query_breed}"


def color_matches(query_color: str | None, animal: Animal) -> tuple[bool, str | None]:
    """Tests whether the animal's color matches the requested color.

    Same strategy as breed_matches: direct substring first, then Hebrew
    aliases via ENGLISH_TO_HEBREW_COLORS.

    Args:
        query_color: The color the user asked for, or None.
        animal: The animal being scored.

    Returns:
        (True, None) on match or no preference.
        (False, "color does not clearly match: X") otherwise.
    """
    if not query_color:
        return True, None

    wanted = query_color.lower().strip()
    animal_color = normalize_text(animal.color)
    animal_text = combined_animal_text(animal)

    if wanted in animal_color or wanted in animal_text:
        return True, None

    hebrew_options = ENGLISH_TO_HEBREW_COLORS.get(wanted, [])

    for option in hebrew_options:
        if option in animal_color or option in animal_text:
            return True, None

    return False, f"color does not clearly match: {query_color}"


def trait_matches(query: AdoptionQuery, animal: Animal) -> tuple[int, list[str], list[str]]:
    """Scores how many requested personality traits surface in the animal's text.

    Args:
        query: The adoption query.
        animal: The animal being scored.

    Returns:
        A 3-tuple of (score, reasons, missing):
          - score: cumulative trait score (2 per matched trait).
          - reasons: list of "matches trait: X" strings to show the user.
          - missing: list of "trait not clearly found: X" strings.
    """
    score = 0
    reasons: list[str] = []
    missing: list[str] = []

    text = combined_animal_text(animal)

    for trait in query.personality_traits:
        trait_normalized = trait.lower().strip()
        keywords = HEBREW_TRAIT_KEYWORDS.get(trait_normalized, [])

        matched = False

        if trait_normalized in text:
            matched = True

        if any(keyword in text for keyword in keywords):
            matched = True

        if matched:
            score += 2
            reasons.append(f"matches trait: {trait}")
        else:
            missing.append(f"trait not clearly found: {trait}")

    return score, reasons, missing


def free_text_overlap_score(query: AdoptionQuery, animal: Animal) -> tuple[int, list[str]]:
    """Counts how many user-query words appear verbatim in the animal's text.

    Filters out short words (<3 chars) and IGNORED_WORDS so
    common filler doesn't inflate the score.

    Args:
        query: The adoption query.
        animal: The animal being scored.

    Returns:
        A 2-tuple of (score, sample_words):
          - score: number of overlapping words, capped at 5.
          - sample_words: up to 5 of those words, for display in reasons.
    """
    query_words = {
        word.lower()
        for word in re.findall(r"[\w\u0590-\u05FF']+", query.free_text)
        if len(word) >= 3
    }

    animal_text = combined_animal_text(animal)
    useful_words = query_words - IGNORED_WORDS
    overlap = [word for word in useful_words if word in animal_text]

    return min(len(overlap), 5), overlap[:5]


def score_animal(query: AdoptionQuery, animal: Animal) -> PartialMatch | None:
    """Scores one animal against the query. Hard filters first, soft scoring after.

    Args:
        query: The user's structured adoption preferences.
        animal: One animal to score.

    Returns:
        A PartialMatch if the animal passed the hard filters and earned a
        positive score, None if it was excluded or scored zero.
    """
    score = 0
    reasons: list[str] = []
    missing: list[str] = []

    # Hard filter by animal type.
    if query.animal_type != AnimalType.unknown:
        if animal.animal_type == query.animal_type:
            score += 5
            reasons.append(f"is a {query.animal_type.value}")
        else:
            return None

    # Hard filter by gender.
    if query.gender != Gender.unknown:
        if animal.gender == query.gender:
            score += 3
            reasons.append(f"gender is {query.gender.value}")
        else:
            return None

    # Soft match by age.
    age_ok, age_reason = age_matches(query, animal)

    if age_ok:
        if query.age_preference:
            score += 3
            reasons.append(f"age matches preference: {query.age_preference}")
    else:
        missing.append(age_reason or "age does not match")

    # Soft match by breed.
    breed_ok, breed_reason = breed_matches(query.breed, animal)

    if breed_ok:
        if query.breed:
            score += 3
            reasons.append(f"breed matches: {query.breed}")
    else:
        missing.append(breed_reason or "breed does not match")

    # Soft match by color.
    color_ok, color_reason = color_matches(query.color, animal)

    if color_ok:
        if query.color:
            score += 2
            reasons.append(f"color matches: {query.color}")
    else:
        missing.append(color_reason or "color does not clearly match")

    # Soft match by personality traits.
    trait_score, trait_reasons, trait_missing = trait_matches(query, animal)
    score += trait_score
    reasons.extend(trait_reasons)
    missing.extend(trait_missing)

    # Soft match by raw free-text overlap.
    overlap_score, overlap_words = free_text_overlap_score(query, animal)

    if overlap_score:
        score += overlap_score
        reasons.append(f"text similarity: {', '.join(overlap_words)}")

    if score <= 0:
        return None

    return PartialMatch(
        animal=animal,
        score=score,
        reasons=reasons,
        missing_or_uncertain=missing,
    )


def find_matches(query: AdoptionQuery, limit: int = 5) -> tuple[list[Animal], list[PartialMatch]]:
    """Top-level entry point: load -> score every animal -> split full vs partial.

    Calls load_animals() to read data/animals.json, runs score_animal
    on each, sorts by score descending, and caps to limit.

    Args:
        query: The user's structured adoption preferences.
        limit: Max number of partial matches to return.

    Returns:
        A 2-tuple (full_matches, partial_matches):
          - full_matches: animals from the top-N partial matches whose
            missing_or_uncertain is empty.
          - partial_matches: top-N PartialMatch objects sorted by score.
    """
    animals = load_animals()

    scored: list[PartialMatch] = []

    for animal in animals:
        match = score_animal(query, animal)

        if match:
            scored.append(match)

    scored.sort(key=lambda item: item.score, reverse=True)

    partial_matches = scored[:limit]

    full_matches = [
        item.animal
        for item in partial_matches
        if not item.missing_or_uncertain
    ]

    return full_matches, partial_matches