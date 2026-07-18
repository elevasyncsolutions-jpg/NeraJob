"""Adzuna Jobs API multi-country adapter with offline fallback."""

from __future__ import annotations

import asyncio
import hashlib
import os

from nerajob.http import ScraperHTTPClient
from nerajob.models import JobPosting
from nerajob.scrapers.base import BaseScraper

_OFFLINE = [
    (
        "Senior Python Developer",
        "Adzuna Demo Corp",
        "New York, NY",
        ["python", "django", "aws"],
        "https://adzuna.com/jobs/senior-python-dev",
    ),
    (
        "Frontend Engineer",
        "UI Masters Ltd",
        "London, UK",
        ["react", "typescript", "css"],
        "https://adzuna.com/jobs/frontend-engineer",
    ),
    (
        "DevOps Engineer",
        "CloudStack GmbH",
        "Berlin, Germany",
        ["kubernetes", "terraform", "ci-cd"],
        "https://adzuna.com/jobs/devops-engineer",
    ),
]

_DEFAULT_COUNTRY = "us"


class AdzunaScraper(BaseScraper):
    """https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"""

    name = "adzuna"
    API_URL = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self, country: str = _DEFAULT_COUNTRY) -> None:
        self.country = country.strip().lower() or _DEFAULT_COUNTRY

    def search(self, query: str, location: str = "", limit: int = 20) -> list[JobPosting]:
        if os.getenv("NERAJOB_ADZUNA_OFFLINE", "").strip().lower() in {"1", "true", "yes"}:
            return self._offline(query, limit)
        app_id = os.getenv("ADZUNA_APP_ID", "")
        api_key = os.getenv("ADZUNA_API_KEY", "")
        if not app_id or not api_key:
            return self._offline(query, limit)
        try:
            return asyncio.run(self._async_search(query, location, limit, app_id, api_key))
        except Exception:
            return self._offline(query, limit)

    async def _async_search(
        self, query: str, location: str, limit: int, app_id: str, api_key: str
    ) -> list[JobPosting]:
        client = ScraperHTTPClient()
        jobs: list[JobPosting] = []
        q = query.strip().lower()
        loc = location.strip().lower()
        page = 1
        try:
            while len(jobs) < limit:
                url = f"{self.API_URL}/{self.country}/search/{page}"
                params: dict[str, object] = {
                    "app_id": app_id,
                    "app_key": api_key,
                    "results_per_page": min(limit, 50),
                }
                if q:
                    params["what"] = q
                if loc:
                    params["where"] = loc
                resp = await client.get(url, params=params)
                payload = resp.json()
                results = payload.get("results") if isinstance(payload, dict) else None
                if not isinstance(results, list) or not results:
                    break
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get("title") or "").strip()
                    company = (
                        str(item.get("company") or {}).get("display_name")
                        if isinstance(item.get("company"), dict)
                        else str(item.get("company") or "")
                    )
                    if isinstance(company, dict):
                        company = ""
                    company = str(company).strip()
                    if not title:
                        continue
                    tags = []
                    category = item.get("category")
                    if isinstance(category, dict):
                        label = str(category.get("label") or "").strip().lower()
                        if label:
                            tags.append(label)
                    place = (
                        str(item.get("location") or {}).get("display_name")
                        if isinstance(item.get("location"), dict)
                        else str(item.get("location") or "Remote")
                    )
                    if isinstance(place, dict):
                        place = str(item.get("location", {}).get("display_name") or "Remote")
                    desc = str(item.get("description") or "")
                    hay = f"{title} {company} {place} {' '.join(tags)} {desc}".lower()
                    if q and q not in hay:
                        continue
                    if loc and loc not in place.lower():
                        continue
                    raw_id = str(item.get("id") or title)
                    digest = hashlib.sha1(f"{self.name}:{raw_id}".encode()).hexdigest()[:12]
                    salary_str = ""
                    salary_min = item.get("salary_min")
                    salary_max = item.get("salary_max")
                    if salary_min and salary_max:
                        salary_str = f"{salary_min}-{salary_max}"
                    elif salary_min:
                        salary_str = str(salary_min)
                    elif salary_max:
                        salary_str = str(salary_max)
                    jobs.append(
                        JobPosting(
                            id=f"adzuna-{digest}",
                            source=self.name,
                            title=title,
                            company=company or "Unknown",
                            location=place,
                            url=str(item.get("redirect_url") or ""),
                            description=desc[:4000],
                            tags=tags[:20],
                            salary=salary_str,
                            remote="remote" in place.lower(),
                            raw={"adzuna_id": raw_id, "country": self.country},
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
            digest = hashlib.sha1(f"{self.name}:{title}:{company}".encode()).hexdigest()[:12]
            out.append(
                JobPosting(
                    id=f"adzuna-{digest}",
                    source=self.name,
                    title=title,
                    company=company,
                    location=place,
                    url=url,
                    description=f"{title} at {company} (offline Adzuna sample).",
                    tags=tags,
                    remote="remote" in place.lower(),
                    raw={"offline": True, "country": self.country},
                )
            )
            if len(out) >= limit:
                break
        return out
