from pathlib import Path

from utils.models import AnimalType


HEBREW_TRAIT_KEYWORDS: dict[str, list[str]] = {
    "friendly": ["חברותי", "חברותית", "חברותיים", "מסתדר", "מסתדרת"],
    "sweet": ["מתוק", "מתוקה", "מקסים", "מקסימה", "מדהים", "מדהימה"],
    "calm": ["רגוע", "רגועה", "שקט", "שקטה", "עדין", "עדינה", "נעימה", "נעים"],
    "playful": ["שובב", "שובבה", "לשחק", "משחק", "משחקת"],
    "energetic": ["אנרגטי", "אנרגטית", "אנרגיה"],
    "cuddly": ["מתלטף", "מתלטפת", "פינוק", "פינוקים", "להתפנק", "חיבוקים"],
    "good with people": ["אוהב אנשים", "אוהבת אנשים", "בני אדם", "אוהב מגע", "אוהבת מגע"],
    "good with dogs": ["מסתדר עם כלבים", "מסתדרת עם כלבים", "כלבים אחרים"],
    "good with cats": ["מסתדר עם חתולים", "מסתדרת עם חתולים", "חתולים"],
    "trained": ["מאולף", "מאולפת", "ממושמע", "ממושמעת"],
    "house trained": ["מחונך לצרכים", "מחונכת לצרכים", "מורגל לארגז", "מורגלת לארגז"],
    "gentle": ["עדין", "עדינה", "נעים", "נעימה", "רגיש", "רגישה"],
    "independent": ["עצמאי", "עצמאית"],
}

ENGLISH_TO_HEBREW_BREEDS: dict[str, list[str]] = {
    "border collie": ["בורדר קולי"],
    "malinois": ["מלינואה", "רועה בלגי"],
    "belgian shepherd": ["רועה בלגי", "מלינואה"],
    "german shepherd": ["רועה גרמני"],
    "husky": ["האסקי", "האסקי סיבירי"],
    "siberian husky": ["האסקי", "האסקי סיבירי"],
    "pitbull": ["פיטבול", "פיטבולית"],
    "american bulldog": ["בולדוג אמריקאי"],
}

ENGLISH_TO_HEBREW_COLORS: dict[str, list[str]] = {
    "black": ["שחור"],
    "white": ["לבן"],
    "black and white": ["שחור לבן", "שחור-לבן"],
    "gray": ["אפור"],
    "grey": ["אפור"],
    "brown": ["חום"],
    "brown and white": ["חום-לבן", "חום לבן"],
    "orange": ["ג'ינג'י", "גינגי", "כתום"],
    "ginger": ["ג'ינג'י", "גינגי", "כתום"],
    "tabby": ["מנומר"],
    "spotted": ["מנומר"],
    "beige": ["בז"],
}

# Common filler words that should NOT count as overlap signal in
IGNORED_WORDS: set[str] = {
    "want", "find", "looking", "animal", "adopt", "please", "with", "that",
    "אני", "רוצה", "מחפש", "מחפשת", "לאמץ", "בבקשה",
    "כלב", "כלבה", "חתול", "חתולה",
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

HEBREW_MALE = "זכר"
HEBREW_FEMALE = "נקבה"
HEBREW_DETAILS_BUTTON = "לפרטים"

HEBREW_MONTH_WORDS = ("חודשים", "חודש")
HEBREW_YEAR_WORDS = ("שנים", "שנה")
HEBREW_AGE_WORDS = HEBREW_YEAR_WORDS + HEBREW_MONTH_WORDS

BASE_URL = "https://yad4.co.il"

SEARCH_URLS = {
    AnimalType.dog: "https://yad4.co.il/search?type=כלב",
    AnimalType.cat: "https://yad4.co.il/search?type=חתול",
}

# Scraper output goes to backend/data/animals.json (sibling of utils/).
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "animals.json"

# Small amount just to have data to work on.
MAX_ANIMALS_PER_TYPE = 30

# Avoid hammering the website.
SCROLL_DELAY_SECONDS = 1.2
