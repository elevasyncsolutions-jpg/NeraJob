"""Himalayas.app public remote jobs API adapter with offline fallback."""

from __future__ import annotations

import asyncio
import hashlib
import os

from nerajob.http import ScraperHTTPClient
from nerajob.models import JobPosting
from nerajob.scrapers.base import BaseScraper

_OFFLINE = [
    (
        "Remote Python Engineer",
        "Himalayas Demo",
        "Remote",
        ["python", "fastapi", "postgres"],
        "https://himalayas.app/jobs/remote-python-engineer",
    ),
    (
        "Senior React Developer",
        "WebFront Co",
        "Remote",
        ["react", "typescript", "frontend"],
        "https://himalayas.app/jobs/senior-react-dev",
    ),
    (
        "DevOps Engineer",
        "CloudScale Inc",
        "Remote",
        ["aws", "kubernetes", "terraform"],
        "https://himalayas.app/jobs/devops-engineer",
    ),
]


class HimalayasScraper(BaseScraper):
    """https://himalayas.app/jobs/api"""

    name = "himalayas"
    API_URL = "https://himalayas.app/jobs/api"

    def search(self, query: str, location: str = "", limit: int = 20) -> list[JobPosting]:
        if os.getenv("NERAJOB_HIMALAYAS_OFFLINE", "").strip().lower() in {"1", "true", "yes"}:
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
                resp = await client.get(f"{self.API_URL}?page={page}")
                payload = resp.json()
                data = payload if isinstance(payload, list) else payload.get("data") or []
                if not isinstance(data, list) or not data:
                    break
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get("title") or "").strip()
                    company = str(item.get("company") or item.get("company_name") or "").strip()
                    if not title:
                        continue
                    tags = [str(t).lower() for t in (item.get("tags") or []) if t]
                    place = str(item.get("location") or "Remote")
                    hay = f"{title} {company} {place} {' '.join(tags)}".lower()
                    if q and q not in hay:
                        continue
                    if loc and loc not in place.lower() and "remote" not in place.lower():
                        continue
                    raw_id = str(item.get("id") or item.get("slug") or title)
                    digest = hashlib.sha1(f"{self.name}:{raw_id}".encode()).hexdigest()[:12]
                    jobs.append(
                        JobPosting(
                            id=f"himalayas-{digest}",
                            source=self.name,
                            title=title,
                            company=company or "Unknown",
                            location=place,
                            url=str(item.get("url") or ""),
                            description=str(item.get("description") or "")[:4000],
                            tags=tags[:20],
                            remote="remote" in place.lower(),
                            raw={"himalayas_id": raw_id},
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
                    id=f"himalayas-{digest}",
                    source=self.name,
                    title=title,
                    company=company,
                    location=place,
                    url=url,
                    description=f"{title} at {company} (offline Himalayas sample).",
                    tags=tags,
                    remote=True,
                    raw={"offline": True},
                )
            )
            if len(out) >= limit:
                break
        return out
