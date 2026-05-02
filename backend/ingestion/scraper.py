import asyncio
import json
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page, Locator

from utils.constants import (
    HEBREW_AGE_WORDS,
    HEBREW_DETAILS_BUTTON,
    HEBREW_FEMALE,
    HEBREW_MALE,
    USER_AGENT,
    BASE_URL, 
    SEARCH_URLS,
    OUTPUT_FILE,
    MAX_ANIMALS_PER_TYPE,
    SCROLL_DELAY_SECONDS
)
from ingestion.llm_extractor import extract_animal_with_llm
from utils.models import Animal, AnimalType
from utils.logger import Logger

logger = Logger("ingest")

async def auto_scroll(page: Page, max_scrolls: int = 8) -> None:
    """Scrolls the page so lazy-loaded cards/images are loaded.

    Args:
        page: The Playwright page to scroll.
        max_scrolls: How many wheel events to dispatch before stopping.
    """
    for _ in range(max_scrolls):
        await page.mouse.wheel(0, 2000)
        await page.wait_for_timeout(int(SCROLL_DELAY_SECONDS * 1000))


async def get_image_url(card: Locator) -> str | None:
    """Tries to find an image URL inside a card.

    Args:
        card: The Playwright Locator pointing at one card element.

    Returns:
        The first found image URL, or None if no image is found.
    """
    images = await card.locator("img").all()

    for img in images:
        src = await img.get_attribute("src")
        if src:
            return urljoin(BASE_URL, src)

        data_src = await img.get_attribute("data-src")
        if data_src:
            return urljoin(BASE_URL, data_src)

    return None


async def get_profile_url(card: Locator) -> str | None:
    """Tries to find the animal details page URL from the card.

    The card itself is often an <a> (per `collect_candidate_cards` heuristic),
    so check its own href first, fall back to inner anchors.

    Args:
        card: The Playwright Locator pointing at one card element.

    Returns:
        Absolute URL to the animal's profile page, or None if no link is found.
    """
    own_href = await card.get_attribute("href")
    if own_href:
        return urljoin(BASE_URL, own_href)

    for link in await card.locator("a").all():
        href = await link.get_attribute("href")
        if href:
            return urljoin(BASE_URL, href)

    return None


async def collect_candidate_cards(page: Page) -> list[Locator]:
    """Collects anchors that look like animal cards.

    The site is React/MUI-based, so class names may change. Instead of
    relying on fragile CSS selectors, we collect anchors that contain
    meaningful animal text (gender + either a "details" button or an
    age-word hint).

    Args:
        page: The Playwright page already loaded with the listing.

    Returns:
        A list of Locators, each pointing at one likely-card anchor.
    """
    possible_cards = await page.locator("a").all()

    cards: list[Locator] = []

    for card in possible_cards:
        try:
            text = (await card.inner_text()).strip()
        except Exception:
            continue

        if not text:
            continue

        has_gender = HEBREW_MALE in text or HEBREW_FEMALE in text
        has_details_button = HEBREW_DETAILS_BUTTON in text
        has_age_hint = any(word in text for word in HEBREW_AGE_WORDS)

        if has_gender and (has_details_button or has_age_hint):
            cards.append(card)

    return cards


async def scrape_search_page(
    page: Page,
    animal_type: AnimalType,
    search_url: str,
) -> list[Animal]:
    """Scrapes one yad4 search-results page and returns extracted animals.

    Args:
        page: The Playwright page to use for navigation.
        animal_type: dog or cat (passed straight into each Animal record).
        search_url: The yad4 search URL to load.

    Returns:
        A list of Animal records extracted from up to MAX_ANIMALS_PER_TYPE cards.
    """
    logger.info(f"Scraping {animal_type.value}: {search_url}")

    await page.goto(search_url, wait_until="networkidle")
    await page.wait_for_timeout(2000)

    await auto_scroll(page)

    cards = await collect_candidate_cards(page)

    logger.info(f"Found {len(cards)} candidate cards for {animal_type.value}")

    animals: list[Animal] = []

    for index, card in enumerate(cards[:MAX_ANIMALS_PER_TYPE], start=1):
        try:
            raw_text = (await card.inner_text()).strip()
            image_url = await get_image_url(card)
            profile_url = await get_profile_url(card)

            if not raw_text:
                continue

            animal = extract_animal_with_llm(
                raw_text=raw_text,
                animal_type=animal_type,
                image_url=image_url,
                profile_url=profile_url,
            )

            animals.append(animal)
            logger.info(f"[{animal_type.value}] {index}/{len(cards)} scraped: {animal.name}")

        except Exception as exc:
            logger.error(f"Failed to parse card {index}: {exc}")

    return animals


async def main() -> None:
    """Runs the full scrape for both dogs and cats and writes data/animals.json.

    Returns:
        None - the result is persisted to OUTPUT_FILE.
    """
    all_animals: list[Animal] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            locale="he-IL",
            viewport={"width": 1440, "height": 1200},
            user_agent=USER_AGENT,
        )

        page = await context.new_page()

        for animal_type, url in SEARCH_URLS.items():
            animals = await scrape_search_page(
                page=page,
                animal_type=animal_type,
                search_url=url,
            )
            all_animals.extend(animals)

        await browser.close()

    # Deduplicate by profile URL if available, otherwise by name + raw text.
    unique: dict[str, Animal] = {}

    for animal in all_animals:
        key = animal.profile_url or f"{animal.animal_type}:{animal.name}:{animal.raw_text[:80]}"
        unique[key] = animal

    data = [animal.model_dump(mode="json") for animal in unique.values()]

    OUTPUT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(f"Saved {len(data)} animals to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
