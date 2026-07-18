"""Arbeitnow EU-focused jobs adapter (builds on ArbeitnowScraper pattern, adds EU country filtering)."""

from __future__ import annotations

import asyncio
import hashlib
import os

from nerajob.http import ScraperHTTPClient
from nerajob.models import JobPosting
from nerajob.scrapers.base import BaseScraper

# EU country keywords to filter by
_EU_COUNTRIES = [
    "austria",
    "belgium",
    "bulgaria",
    "croatia",
    "cyprus",
    "czech",
    "denmark",
    "estonia",
    "finland",
    "france",
    "germany",
    "greece",
    "hungary",
    "ireland",
    "italy",
    "latvia",
    "lithuania",
    "luxembourg",
    "malta",
    "netherlands",
    "poland",
    "portugal",
    "romania",
    "slovakia",
    "slovenia",
    "spain",
    "sweden",
    "berlin",
    "munich",
    "paris",
    "amsterdam",
    "dublin",
    "madrid",
    "barcelona",
    "lisbon",
    "prague",
    "warsaw",
    "vienna",
    "copenhagen",
    "stockholm",
    "helsinki",
    "brussels",
    "zurich",
]

_OFFLINE = [
    (
        "Backend Engineer (Python)",
        "Arbeitnow EU GmbH",
        "Berlin, Germany / Remote",
        ["python", "django", "remote"],
        "https://www.arbeitnow.com/view/demo-eu-python-backend",
    ),
    (
        "DevOps Engineer",
        "Cloud EU North",
        "Remote EU",
        ["kubernetes", "terraform", "aws"],
        "https://www.arbeitnow.com/view/demo-eu-devops",
    ),
    (
        "Security Engineer",
        "Shield EU",
        "Remote",
        ["security", "python", "appsec"],
        "https://www.arbeitnow.com/view/demo-eu-security",
    ),
]


class ArbeitnowEUScraper(BaseScraper):
    """https://www.arbeitnow.com/api/job-board-api with EU-country filtering."""

    name = "arbeitnow_eu"
    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, country: str = "") -> None:
        self._country = country.strip().lower()

    def search(self, query: str, location: str = "", limit: int = 20) -> list[JobPosting]:
        if os.getenv("NERAJOB_ARBEITNOW_EU_OFFLINE", "").strip().lower() in {"1", "true", "yes"}:
            return self._offline(query, limit)
        try:
            return asyncio.run(self._async_search(query, location, limit))
        except Exception:
            return self._offline(query, limit)

    async def _async_search(self, query: str, location: str, limit: int) -> list[JobPosting]:
        client = ScraperHTTPClient()
        jobs: list[JobPosting] = []
        q = query.strip().lower()
        loc = location.strip().lower()
        page = 1
        try:
            while len(jobs) < limit:
                params: dict[str, object] = {"page": page}
                resp = await client.get(self.API_URL, params=params)
                payload = resp.json()
                data = payload.get("data") if isinstance(payload, dict) else None
                if not isinstance(data, list) or not data:
                    break
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get("title") or "").strip()
                    company = str(item.get("company_name") or "").strip()
                    if not title:
                        continue
                    tags = [str(t).lower() for t in (item.get("tags") or []) if t]
                    place = str(item.get("location") or "Remote").lower()
                    desc = str(item.get("description") or "")
                    hay = f"{title} {company} {place} {' '.join(tags)} {desc}".lower()
                    if q and q not in hay:
                        continue
                    if loc and loc not in place:
                        continue

                    # EU filter: check if location mentions EU country or self._country
                    place_lower = place.lower()
                    if self._country and self._country not in place_lower:
                        continue
                    if not self._country:
                        is_eu = any(eu.lower() in place_lower for eu in _EU_COUNTRIES)
                        if not is_eu and "remote" not in place_lower:
                            continue

                    raw_id = str(item.get("slug") or item.get("url") or title)
                    digest = hashlib.sha1(f"{self.name}:{raw_id}".encode()).hexdigest()[:12]
                    jobs.append(
                        JobPosting(
                            id=f"arbeitnow_eu-{digest}",
                            source=self.name,
                            title=title,
                            company=company or "Unknown",
                            location=str(item.get("location") or "Remote"),
                            url=str(item.get("url") or ""),
                            description=desc[:4000],
                            tags=tags[:20],
                            remote="remote" in place,
                            raw={"slug": raw_id, "country_filter": self._country},
                        )
                    )
                    if len(jobs) >= limit:
                        break
                page += 1
        except Exception:
            pass
        finally:
            await client.aclose()
        return jobs if jobs else self._offline(query, limit)

    def _offline(self, query: str, limit: int) -> list[JobPosting]:
        q = query.strip().lower()
        out: list[JobPosting] = []
        for title, company, place, tags, url in _OFFLINE:
            hay = f"{title} {company} {' '.join(tags)}".lower()
            if q and q not in hay:
                continue
            digest = hashlib.sha1(f"{self.name}:{title}".encode()).hexdigest()[:12]
            out.append(
                JobPosting(
                    id=f"arbeitnow_eu-{digest}",
                    source=self.name,
                    title=title,
                    company=company,
                    location=place,
                    url=url,
                    description=f"{title} at {company} (offline Arbeitnow EU sample).",
                    tags=tags,
                    remote="remote" in place.lower(),
                    raw={"offline": True, "country_filter": self._country},
                )
            )
            if len(out) >= limit:
                break
        return out
