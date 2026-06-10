"""
GlobalScholar Travel Safety Scraper
====================================
Fetches travel advisory data from the US State Department's travel
advisory page (https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html/)
and maps each country's advisory level directly onto our University records.

Run via management command:
    python manage.py run_scraper
    python manage.py run_scraper --country "Germany"
    python manage.py run_scraper --dry-run
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

ADVISORY_URL = (
    "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html/"
)

REQUEST_TIMEOUT_SECONDS = 15

# Polite delay between requests if we ever paginate or hit sub-pages.
CRAWL_DELAY_SECONDS = 1.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GlobalScholarBot/1.0; "
        "+https://globalscholar.example.com/bot)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Maps the text strings the State Dept uses → our AdvisoryLevel choice keys.
# We keep this explicit so a wording change on their side triggers a clear
# log warning rather than silently storing garbage data.
LEVEL_TEXT_MAP = {
    "level 1": "LEVEL_1",
    "level 2": "LEVEL_2",
    "level 3": "LEVEL_3",
    "level 4": "LEVEL_4",
    "exercise normal precautions": "LEVEL_1",
    "exercise increased caution": "LEVEL_2",
    "reconsider travel": "LEVEL_3",
    "do not travel": "LEVEL_4",
}


# ── Data container ─────────────────────────────────────────────────────────────

@dataclass
class AdvisoryRecord:
    """Holds the scraped advisory data for one country before DB write."""
    country: str
    advisory_level: str          # Our AdvisoryLevel choice key, e.g. "LEVEL_2"
    advisory_text: str           # Raw text from the page for audit logs
    source_url: str


# ── Core scraper class ────────────────────────────────────────────────────────

class TravelSafetyScraper:
    """
    Fetches and parses the State Department advisory page.
    Entirely decoupled from Django ORM — returns plain AdvisoryRecord
    objects so it is unit-testable without a database.
    """

    def __init__(self, timeout: int = REQUEST_TIMEOUT_SECONDS):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_page(self, url: str) -> Optional[str]:
        """
        Downloads the raw HTML for a given URL.
        Returns the HTML string on success, None on any network failure.
        Uses explicit if/else — no bare except swallowing errors silently.
        """
        response = self.session.get(url, timeout=self.timeout)

        if response.status_code == 200:
            logger.info("Successfully fetched %s (%d bytes)", url, len(response.content))
            return response.text
        elif response.status_code == 403:
            logger.error(
                "Access denied (403) fetching %s. The site may be blocking scrapers.", url
            )
            return None
        elif response.status_code == 404:
            logger.error("Page not found (404): %s", url)
            return None
        elif response.status_code >= 500:
            logger.error(
                "Server error (%d) fetching %s. The source site may be down.",
                response.status_code,
                url,
            )
            return None
        else:
            logger.warning(
                "Unexpected HTTP %d fetching %s.", response.status_code, url
            )
            return None

    def parse_advisories(self, html: str) -> list[AdvisoryRecord]:
        """
        Parses the State Department advisory table from raw HTML.

        The page renders a table where each row contains:
          <td> Country Name </td>
          <td> Level N: Advisory Text </td>

        Returns a list of AdvisoryRecord objects.
        """
        soup = BeautifulSoup(html, "html.parser")
        records = []

        # The advisory data lives inside a table with class "table-data"
        # on the State Department page.
        advisory_table = soup.find("table", {"class": "table-data"})

        if advisory_table is None:
            # Fall back: try any table on the page that has advisory-looking rows.
            advisory_table = soup.find("table")

        if advisory_table is None:
            logger.error(
                "Could not locate the advisory table in the page HTML. "
                "The State Department may have changed their page structure."
            )
            return records

        rows = advisory_table.find_all("tr")

        for row in rows:
            cells = row.find_all("td")

            if len(cells) < 2:
                # Header row or malformed row — skip.
                continue

            country_text = cells[0].get_text(strip=True)
            advisory_text = cells[1].get_text(strip=True)

            if not country_text or not advisory_text:
                continue

            advisory_level = self._map_level(advisory_text)

            if advisory_level is None:
                logger.warning(
                    "Could not map advisory text to a known level for '%s': '%s'",
                    country_text,
                    advisory_text,
                )
                advisory_level = "UNKNOWN"

            records.append(
                AdvisoryRecord(
                    country=country_text,
                    advisory_level=advisory_level,
                    advisory_text=advisory_text,
                    source_url=ADVISORY_URL,
                )
            )

        logger.info("Parsed %d advisory records from page.", len(records))
        return records

    def _map_level(self, advisory_text: str) -> Optional[str]:
        """
        Maps a raw advisory string like "Level 2: Exercise Increased Caution"
        to our internal choice key "LEVEL_2".

        Checks each known keyword against the lowercased text using explicit
        if/else so mapping misses are never silently ignored.
        """
        lowered = advisory_text.lower()

        for keyword, level_key in LEVEL_TEXT_MAP.items():
            if keyword in lowered:
                return level_key

        return None

    def scrape(self) -> list[AdvisoryRecord]:
        """
        Full scrape pipeline: fetch → parse → return records.
        Entry point called by the management command.
        """
        logger.info("Starting travel advisory scrape from: %s", ADVISORY_URL)
        html = self.fetch_page(ADVISORY_URL)

        if html is None:
            logger.error("Scrape aborted — could not retrieve page HTML.")
            return []

        records = self.parse_advisories(html)
        return records


# ── Django ORM updater ────────────────────────────────────────────────────────

class UniversityAdvisoryUpdater:
    """
    Takes a list of AdvisoryRecord objects and writes them into the
    University table. Entirely separate from the scraper so each layer
    is independently testable.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            "universities_checked": 0,
            "updated": 0,
            "already_current": 0,
            "no_match_found": 0,
        }

    def update(
        self,
        records: list[AdvisoryRecord],
        country_filter: Optional[str] = None,
    ) -> dict:
        """
        Iterates over University rows and updates travel_advisory_level
        where a matching country is found in the scraped records.

        country_filter: if provided, only updates universities in that country.
        dry_run: logs what would change without writing to the DB.
        """
        # Deferred import keeps this module importable outside Django context.
        from universities.models import University

        # Build a lookup dict: lowercase country name → AdvisoryRecord.
        # If a country appears multiple times in the scraped data (shouldn't
        # happen but defensive), the last entry wins.
        advisory_lookup = {
            record.country.lower(): record for record in records
        }

        universities = University.objects.all()

        if country_filter:
            universities = universities.filter(country__icontains=country_filter)

        for university in universities:
            self.stats["universities_checked"] += 1
            country_key = university.country.lower().strip()

            if country_key in advisory_lookup:
                matched_record = advisory_lookup[country_key]
                self._apply_update(university, matched_record)
            else:
                # No advisory data found for this university's country.
                logger.debug(
                    "No advisory match for university '%s' in country '%s'.",
                    university.name,
                    university.country,
                )
                self.stats["no_match_found"] += 1

        self._log_summary()
        return self.stats

    def _apply_update(self, university, record: AdvisoryRecord) -> None:
        """
        Applies one advisory update to one University row.
        Explicit if/else so the dry_run path is clearly separated.
        """
        from universities.models import University

        new_level = record.advisory_level
        current_level = university.travel_advisory_level

        if new_level == current_level:
            logger.debug(
                "'%s' advisory already current: %s", university.name, current_level
            )
            self.stats["already_current"] += 1
            return

        if self.dry_run:
            logger.info(
                "[DRY RUN] Would update '%s' (%s): %s → %s",
                university.name,
                university.country,
                current_level,
                new_level,
            )
            self.stats["updated"] += 1
        else:
            university.travel_advisory_level = new_level
            university.advisory_last_updated = timezone.now()
            university.save(
                update_fields=["travel_advisory_level", "advisory_last_updated"]
            )
            logger.info(
                "Updated '%s' (%s): %s → %s",
                university.name,
                university.country,
                current_level,
                new_level,
            )
            self.stats["updated"] += 1

    def _log_summary(self) -> None:
        logger.info(
            "Scraper run complete. Checked: %d | Updated: %d | "
            "Already current: %d | No match: %d",
            self.stats["universities_checked"],
            self.stats["updated"],
            self.stats["already_current"],
            self.stats["no_match_found"],
        )