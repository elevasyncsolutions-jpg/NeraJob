from __future__ import annotations

import hashlib

from nerajob.models import JobPosting
from nerajob.scrapers.base import BaseScraper

SAMPLE_ROLES = [
    ("Security Analyst", "Shield Ops", "Remote", ["security", "siem", "python"]),
    ("Growth Marketer", "RemoteOK Demo", "Remote", ["marketing", "growth", "seo"]),
    (
        "Senior Python Backend Engineer",
        "Northwind Labs",
        "Remote",
        ["python", "fastapi", "postgres"],
    ),
    ("Full-Stack Engineer", "Acme Global", "Berlin / Remote", ["python", "vue", "typescript"]),
    ("Platform Engineer", "Orbit Systems", "Singapore", ["python", "kubernetes", "aws"]),
    ("ML Engineer", "DataNest", "Remote", ["python", "pytorch", "mlops"]),
    ("Automation Engineer", "HireFlow", "Ho Chi Minh City", ["python", "scraping", "automation"]),
    ("Rust Systems Engineer", "EdgeForge", "Remote", ["rust", "systems", "linux"]),
    ("Frontend Engineer", "Pixel Harbor", "Remote", ["typescript", "react", "css"]),
    ("Developer Advocate", "OpenDocs", "Remote", ["python", "docs", "community"]),
]


class SampleScraper(BaseScraper):
    """Offline deterministic feed for demos and tests (no network)."""

    name = "sample"

    def search(self, query: str, location: str = "", limit: int = 20) -> list[JobPosting]:
        q = query.strip().lower()
        loc = location.strip().lower()
        jobs: list[JobPosting] = []
        for title, company, place, tags in SAMPLE_ROLES:
            hay = f"{title} {company} {place} {' '.join(tags)}".lower()
            if q and q not in hay:
                continue
            if loc and loc not in place.lower() and loc not in ("remote", "anywhere", "world"):
                if "remote" not in place.lower():
                    continue
            digest = hashlib.sha1(f"{self.name}:{title}:{company}".encode()).hexdigest()[:12]
            jobs.append(
                JobPosting(
                    id=f"sample-{digest}",
                    source=self.name,
                    title=title,
                    company=company,
                    location=place,
                    url=f"https://example.com/jobs/{digest}",
                    description=(
                        f"{title} at {company}. Looking for experience with "
                        f"{', '.join(tags)}. Query matched: {query or 'any'}."
                    ),
                    tags=tags,
                    remote="remote" in place.lower(),
                )
            )
            if len(jobs) >= limit:
                break
        if not jobs and not q:
            # fallback: return first N samples
            for title, company, place, tags in SAMPLE_ROLES[:limit]:
                digest = hashlib.sha1(f"{self.name}:{title}:{company}".encode()).hexdigest()[:12]
                jobs.append(
                    JobPosting(
                        id=f"sample-{digest}",
                        source=self.name,
                        title=title,
                        company=company,
                        location=place,
                        url=f"https://example.com/jobs/{digest}",
                        description=f"{title} at {company}.",
                        tags=tags,
                        remote="remote" in place.lower(),
                    )
                )
        return jobs
