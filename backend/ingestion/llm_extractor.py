"""LLM-driven normalization of one yad4 card's raw text into an Animal record."""
import os

from dotenv import load_dotenv
from openai import OpenAI

from utils.models import Animal, AnimalExtraction, AnimalType

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_animal_with_llm(
    raw_text: str,
    animal_type: AnimalType,
    image_url: str | None,
    profile_url: str | None,
) -> Animal:
    """Normalizes Hebrew/messy card text into a clean Animal Pydantic object.

    Sends the raw card text to gpt-4o-mini with structured-output enforcement, then wraps the LLM-extracted fields
    together with the Playwright-supplied URLs into the canonical Animal.

    Args:
        raw_text: The card's `inner_text` from Playwright. Hebrew, possibly
            messy with line breaks, age phrases, gender words, etc.
        animal_type: Already known from which listing page (dog or cat).
            Passed straight through to the resulting Animal.
        image_url: Card thumbnail URL (or None if Playwright didn't find one).
        profile_url: Detail-page URL (or None).

    Returns:
        Animal: A fully-populated record. Fields the LLM couldn't extract
        are left as None.
    """

    prompt = f"""
        Extract animal adoption data from this Hebrew text.

        Animal type: {animal_type.value}

        Rules:
        - Return only the fields defined in the schema.
        - Translate gender:
        - "זכר" -> "male"
        - "נקבה" -> "female"
        - unknown/missing -> "unknown"
        - Keep age as text, for example: "7 שנים", "2 חודשים".
        - If breed/type appears, extract it.
        - If color is not mentioned, return null.
        - Translate size: "קטן" -> "small", "בינוני" -> "medium", "גדול" -> "large".
          If size is not mentioned, return null.
        - Do not invent missing data.
        - Keep description concise but useful.

        Raw text:
        {raw_text}
        """

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You extract structured animal adoption data from Hebrew web pages.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format=AnimalExtraction,
    )

    extracted: AnimalExtraction = response.choices[0].message.parsed

    return Animal(
        animal_type=animal_type,
        name=extracted.name,
        gender=extracted.gender,
        age=extracted.age,
        breed=extracted.breed,
        color=extracted.color,
        size=extracted.size,
        description=extracted.description,
        image_url=image_url,
        profile_url=profile_url,
        raw_text=raw_text,
    )