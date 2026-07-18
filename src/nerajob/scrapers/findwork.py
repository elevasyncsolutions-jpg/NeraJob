"""Findwork.dev jobs API adapter with offline fallback."""

from __future__ import annotations

import asyncio
import hashlib
import os

from nerajob.http import ScraperHTTPClient
from nerajob.models import JobPosting
from nerajob.scrapers.base import BaseScraper

_OFFLINE = [
    (
        "Backend Engineer (Python)",
        "Findwork Demo Inc",
        "Remote",
        ["python", "django", "rest"],
        "https://findwork.dev/jobs/backend-python-engineer",
    ),
    (
        "Data Scientist",
        "DataPivot",
        "San Francisco, CA",
        ["python", "machine-learning", "sql"],
        "https://findwork.dev/jobs/data-scientist",
    ),
    (
        "Full Stack Developer",
        "StackCraft",
        "Remote",
        ["javascript", "python", "react"],
        "https://findwork.dev/jobs/fullstack-dev",
    ),
]


class FindworkScraper(BaseScraper):
    """https://findwork.dev/api/jobs/"""

    name = "findwork"
    API_URL = "https://findwork.dev/api/jobs/"

    def search(self, query: str, location: str = "", limit: int = 20) -> list[JobPosting]:
        if os.getenv("NERAJOB_FINDWORK_OFFLINE", "").strip().lower() in {"1", "true", "yes"}:
            return self._offline(query, limit)
        try:
            return asyncio.run(self._async_search(query, location, limit))
        except Exception:
            return self._offline(query, limit)

    async def _async_search(self, query: str, location: str, limit: int) -> list[JobPosting]:
        api_key = os.getenv("FINDWORK_API_KEY", "")
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Token {api_key}"

        client = ScraperHTTPClient()
        jobs: list[JobPosting] = []
        q = query.strip().lower()
        loc = location.strip().lower()
        page = 1
        try:
            while len(jobs) < limit:
                params = {"page": page, "page_size": min(limit, 100)}
                if q:
                    params["search"] = q
                resp = await client.get(self.API_URL, params=params, headers=headers)
                payload = resp.json()
                results = payload.get("results") if isinstance(payload, dict) else None
                if not isinstance(results, list) or not results:
                    break
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get("role_name") or item.get("title") or "").strip()
                    company = str(item.get("company_name") or "").strip()
                    if not title:
                        continue
                    tags = [
                        str(t).lower()
                        for t in (item.get("keywords") or item.get("tags") or [])
                        if t
                    ]
                    place = str(item.get("location") or "Remote")
                    text = str(item.get("text") or item.get("description") or "")
                    hay = f"{title} {company} {place} {' '.join(tags)} {text}".lower()
                    if q and q not in hay:
                        continue
                    if loc and loc not in place.lower() and "remote" not in place.lower():
                        continue
                    raw_id = str(item.get("id") or title)
                    digest = hashlib.sha1(f"{self.name}:{raw_id}".encode()).hexdigest()[:12]
                    jobs.append(
                        JobPosting(
                            id=f"findwork-{digest}",
                            source=self.name,
                            title=title,
                            company=company or "Unknown",
                            location=place,
                            url=str(item.get("url") or item.get("application_url") or ""),
                            description=text[:4000],
                            tags=tags[:20],
                            remote="remote" in place.lower(),
                            raw={"findwork_id": raw_id},
                        )
                    )
                    if len(jobs) >= limit:
                        break
                if not payload.get("next"):
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
                    id=f"findwork-{digest}",
                    source=self.name,
                    title=title,
                    company=company,
                    location=place,
                    url=url,
                    description=f"{title} at {company} (offline Findwork sample).",
                    tags=tags,
                    remote="remote" in place.lower(),
                    raw={"offline": True},
                )
            )
            if len(out) >= limit:
                break
        return out
