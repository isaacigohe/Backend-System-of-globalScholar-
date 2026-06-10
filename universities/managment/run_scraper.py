"""
Management command: run_scraper
================================
Usage:
    python manage.py run_scraper
    python manage.py run_scraper --country "Germany"
    python manage.py run_scraper --dry-run
    python manage.py run_scraper --country "France" --dry-run
"""

import logging

from django.core.management.base import BaseCommand

from universities.scraper import TravelSafetyScraper, UniversityAdvisoryUpdater

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Scrapes the US State Department travel advisory page and updates "
        "the travel_advisory_level field on University records."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            type=str,
            default=None,
            help=(
                "Limit updates to universities in a specific country. "
                "Example: --country 'Germany'"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help=(
                "Log what would be updated without writing any changes to the database."
            ),
        )

    def handle(self, *args, **options):
        country_filter = options.get("country")
        dry_run = options.get("dry_run")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN mode — no database writes will occur.\n")
            )

        if country_filter:
            self.stdout.write(f"Filtering updates to country: {country_filter}\n")

        # ── Step 1: Scrape ────────────────────────────────────────────────────
        self.stdout.write("Fetching travel advisories from State Department...\n")
        scraper = TravelSafetyScraper()
        records = scraper.scrape()

        if not records:
            self.stdout.write(
                self.style.ERROR(
                    "Scrape returned zero records. Check network access and logs.\n"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"Fetched {len(records)} advisory records.\n")
        )

        # ── Step 2: Update DB ─────────────────────────────────────────────────
        self.stdout.write("Matching records to University table...\n")
        updater = UniversityAdvisoryUpdater(dry_run=dry_run)
        stats = updater.update(records, country_filter=country_filter)

        # ── Step 3: Report ────────────────────────────────────────────────────
        self.stdout.write("\n── Scraper Run Summary ──────────────────────────")
        self.stdout.write(f"  Universities checked : {stats['universities_checked']}")
        self.stdout.write(
            self.style.SUCCESS(f"  Updated              : {stats['updated']}")
        )
        self.stdout.write(f"  Already current      : {stats['already_current']}")
        self.stdout.write(
            self.style.WARNING(f"  No advisory match    : {stats['no_match_found']}")
        )
        self.stdout.write("─────────────────────────────────────────────────\n")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run complete. No changes were saved.\n")
            )
        else:
            self.stdout.write(self.style.SUCCESS("Database updated successfully.\n"))