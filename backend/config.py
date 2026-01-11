from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

INPUT_CONSTITUENTS_FILE = BASE_DIR / "InputConstituents.csv"
INPUT_EMAILS_FILE = BASE_DIR / "InputEmails.csv"
INPUT_DONATION_HISTORY_FILE = BASE_DIR / "InputDonationHistory.csv"

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_CONSTITUENTS_FILE = OUTPUT_DIR / "FinalOutputFormatCueBoxConstituents.csv"
OUTPUT_TAGS_FILE = OUTPUT_DIR / "FinalOutputFormatCueBoxTags.csv"

TAG_API_URL = "https://6719768f7fc4c5ff8f4d84f1.mockapi.io/api/v1/tags"
TAG_API_TIMEOUT = 10

DATE_FORMATS = [
    "%b %d, %Y",      # "Jan 19, 2020"
    "%m/%d/%Y",       # "04/19/2022"
    "%m/%d/%Y %H:%M", # "12/07/2017 12:34"
    "%Y-%m-%d",       # ISO format
]

INVALID_COMPANY_VALUES = ["", "None", "N/A", "n/a", "Retired", "Used to work here."]

TITLE_MAPPING = {
    "mr": "Mr.",
    "mrs": "Mrs.",
    "ms": "Ms.",
    "dr": "Dr.",
    "rev": "",  # Not in allowed list
    "mr. and mrs.": "",  # Not in allowed list
}

EMAIL_DOMAIN_CORRECTIONS = {
    "gmaill.com": "gmail.com",
    "hotmal.com": "hotmail.com",
    "yaho.com": "yahoo.com",
    "gmal.com": "gmail.com",
    "outlok.com": "outlook.com",
}

CONSTITUENT_FIELDS = [
    "CB Constituent ID",
    "CB Constituent Type",
    "CB First Name",
    "CB Last Name",
    "CB Company Name",
    "CB Created At",
    "CB Email 1 (Standardized)",
    "CB Email 2 (Standardized)",
    "CB Title",
    "CB Tags",
    "CB Background Information",
    "CB Lifetime Donation Amount",
    "CB Most Recent Donation Date",
    "CB Most Recent Donation Amount",
]

TAG_OUTPUT_FIELDS = [
    "CB Tag Name",
    "CB Tag Count",
]
