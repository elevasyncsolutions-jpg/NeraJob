"""USAJOBS official API adapter with offline fallback."""

from __future__ import annotations

import asyncio
import hashlib
import os

from nerajob.http import ScraperHTTPClient
from nerajob.models import JobPosting
from nerajob.scrapers.base import BaseScraper

_OFFLINE = [
    (
        "IT Specialist (Systems Administration)",
        "Department of Defense",
        "Washington, DC",
        ["it", "systems", "security"],
        "https://www.usajobs.gov/job/123456",
    ),
    (
        "Data Scientist",
        "National Institutes of Health",
        "Bethesda, MD",
        ["data-science", "python", "statistics"],
        "https://www.usajobs.gov/job/234567",
    ),
    (
        "Software Developer",
        "General Services Administration",
        "Remote",
        ["software", "development", "agile"],
        "https://www.usajobs.gov/job/345678",
    ),
]


class USAJobsScraper(BaseScraper):
    """https://data.usajobs.gov/api/search"""

    name = "usajobs"
    API_URL = "https://data.usajobs.gov/api/search"

    def search(self, query: str, location: str = "", limit: int = 20) -> list[JobPosting]:
        if os.getenv("NERAJOB_USAJOBS_OFFLINE", "").strip().lower() in {"1", "true", "yes"}:
            return self._offline(query, limit)
        email = os.getenv("USAJOBS_EMAIL", "")
        api_key = os.getenv("USAJOBS_API_KEY", "")
        if not email or not api_key:
            return self._offline(query, limit)
        try:
            return asyncio.run(self._async_search(query, location, limit, email, api_key))
        except Exception:
            return self._offline(query, limit)

    async def _async_search(
        self, query: str, location: str, limit: int, email: str, api_key: str
    ) -> list[JobPosting]:
        headers = {
            "Host": "data.usajobs.gov",
            "User-Agent": email,
            "Authorization-Key": api_key,
            "Accept": "application/json",
        }
        client = ScraperHTTPClient()
        jobs: list[JobPosting] = []
        q = query.strip().lower()
        loc = location.strip().lower()
        page = 1
        try:
            while len(jobs) < limit:
                params: dict[str, object] = {
                    "Page": page,
                    "ResultsPerPage": min(limit, 200),
                }
                if q:
                    params["Keyword"] = q
                if loc:
                    params["LocationName"] = loc
                resp = await client.get(self.API_URL, params=params, headers=headers)
                payload = resp.json()
                search_result = payload.get("SearchResult") if isinstance(payload, dict) else None
                if not isinstance(search_result, dict):
                    break
                items = (
                    search_result.get("SearchResultItems")
                    if isinstance(search_result, dict)
                    else None
                )
                if not isinstance(items, list) or not items:
                    break
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    matched = item.get("MatchedObjectDescriptor")
                    if not isinstance(matched, dict):
                        continue
                    title = str(matched.get("PositionTitle") or "").strip()
                    company = str(
                        matched.get("OrganizationName") or matched.get("DepartmentName") or ""
                    ).strip()
                    if not title:
                        continue
                    place_parts = []
                    loc_data = matched.get("PositionLocation")
                    if isinstance(loc_data, list):
                        for loc_item in loc_data:
                            if isinstance(loc_item, dict):
                                city = str(loc_item.get("CityName") or "").strip()
                                state = str(loc_item.get("State") or "").strip()
                                country = str(loc_item.get("CountryName") or "").strip()
                                parts = [p for p in [city, state, country] if p]
                                if parts:
                                    place_parts.append(", ".join(parts))
                    place = place_parts[0] if place_parts else "Remote"
                    tags_raw = matched.get("JobCategory")
                    tags = []
                    if isinstance(tags_raw, list):
                        for cat in tags_raw:
                            if isinstance(cat, dict):
                                name = str(cat.get("Name") or "").strip().lower()
                                if name:
                                    tags.append(name)
                    desc = str(matched.get("JobSummary") or "")
                    hay = f"{title} {company} {place} {' '.join(tags)} {desc}".lower()
                    if q and q not in hay:
                        continue
                    if loc and loc not in place.lower():
                        continue
                    raw_id = str(matched.get("PositionID") or title)
                    digest = hashlib.sha1(f"{self.name}:{raw_id}".encode()).hexdigest()[:12]
                    remote = "remote" in place.lower()
                    salary_str = ""
                    salary_data = matched.get("PositionRemuneration")
                    if isinstance(salary_data, list):
                        for s in salary_data:
                            if isinstance(s, dict):
                                low = str(s.get("MinimumRange") or "")
                                high = str(s.get("MaximumRange") or "")
                                if low and high:
                                    salary_str = f"{low}-{high}"
                                elif low:
                                    salary_str = low
                                if salary_str:
                                    break
                    jobs.append(
                        JobPosting(
                            id=f"usajobs-{digest}",
                            source=self.name,
                            title=title,
                            company=company or "Unknown",
                            location=place,
                            url=str(matched.get("PositionURI") or ""),
                            description=desc[:4000],
                            tags=tags[:20],
                            salary=salary_str,
                            remote=remote,
                            raw={"usajobs_id": raw_id},
                        )
                    )
                    if len(jobs) >= limit:
                        break
                total_pages = 1
                user_area = search_result.get("UserArea")
                if isinstance(user_area, dict):
                    total_pages = int(user_area.get("TotalPages", 1))
                if page >= total_pages:
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
            digest = hashlib.sha1(f"{self.name}:{title}:{company}".encode()).hexdigest()[:12]
            out.append(
                JobPosting(
                    id=f"usajobs-{digest}",
                    source=self.name,
                    title=title,
                    company=company,
                    location=place,
                    url=url,
                    description=f"{title} at {company} (offline USAJobs sample).",
                    tags=tags,
                    remote="remote" in place.lower(),
                    raw={"offline": True},
                )
            )
            if len(out) >= limit:
                break
        return out
