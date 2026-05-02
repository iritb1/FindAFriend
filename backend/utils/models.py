"""Shared Pydantic models used across the backend.

The scraper writes `Animal` records; the matcher reads them; the agent
returns `PartialMatch` objects. All shape definitions live here so there's
exactly one source of truth.
"""
from enum import Enum

from pydantic import BaseModel, Field


class AnimalType(str, Enum):
    dog = "dog"
    cat = "cat"
    unknown = "unknown"


class Gender(str, Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class Size(str, Enum):
    small = "small"
    medium = "medium"
    large = "large"


class Animal(BaseModel):
    """Canonical animal record."""

    source: str = Field(default="yad4")
    animal_type: AnimalType
    name: str | None = None
    gender: Gender = Gender.unknown
    age: str | None = None
    breed: str | None = None
    color: str | None = None
    size: Size | None = None
    description: str | None = None
    image_url: str | None = None
    profile_url: str | None = None
    raw_text: str | None = None


class AnimalExtraction(BaseModel):
    """Fields the LLM extracts from a single card's raw Hebrew text."""

    name: str | None
    gender: Gender
    age: str | None
    breed: str | None
    color: str | None
    size: Size | None
    description: str | None


class AdoptionQuery(BaseModel):
    """Structured search criteria extracted from the user's free-text request."""

    animal_type: AnimalType = AnimalType.unknown
    gender: Gender = Gender.unknown

    age_preference: str | None = Field(
        default=None,
        description="Examples: puppy, kitten, baby, young, adult, senior, any",
    )
    breed: str | None = None
    color: str | None = None

    personality_traits: list[str] = Field(default_factory=list)
    free_text: str


class PartialMatch(BaseModel):
    """An animal that scored against the query, with explanation of fit + gaps."""

    animal: Animal
    score: int
    reasons: list[str]
    missing_or_uncertain: list[str] = Field(default_factory=list)
