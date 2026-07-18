"""Greenhouse public board JSON adapter with offline fallback."""

from __future__ import annotations

import asyncio
import hashlib
import os

from nerajob.http import ScraperHTTPClient
from nerajob.models import JobPosting
from nerajob.scrapers.base import BaseScraper

_OFFLINE = [
    (
        "Senior Software Engineer",
        "MergeOS",
        "Remote",
        ["python", "go", "distributed-systems"],
        "https://boards.greenhouse.io/mergeos/jobs/1",
    ),
    (
        "Product Designer",
        "MergeOS",
        "San Francisco, CA",
        ["design", "ux", "figma"],
        "https://boards.greenhouse.io/mergeos/jobs/2",
    ),
    (
        "Developer Advocate",
        "MergeOS",
        "Remote",
        ["python", "community", "docs"],
        "https://boards.greenhouse.io/mergeos/jobs/3",
    ),
]

_DEFAULT_BOARD = "mergeos"


class GreenhouseScraper(BaseScraper):
    """https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"""

    name = "greenhouse"
    API_URL = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self, board_token: str | None = None) -> None:
        self.board_token = board_token or os.getenv("NERAJOB_GREENHOUSE_BOARD") or _DEFAULT_BOARD

    def search(self, query: str, location: str = "", limit: int = 20) -> list[JobPosting]:
        if os.getenv("NERAJOB_GREENHOUSE_OFFLINE", "").strip().lower() in {"1", "true", "yes"}:
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
                url = f"{self.API_URL}/{self.board_token}/jobs"
                params: dict[str, object] = {"page": page, "per_page": min(limit, 100)}
                resp = await client.get(url, params=params)
                payload = resp.json()
                jobs_list = payload.get("jobs") if isinstance(payload, dict) else None
                if not isinstance(jobs_list, list) or not jobs_list:
                    break
                for item in jobs_list:
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get("title") or "").strip()
                    if not title:
                        continue
                    offices = item.get("offices") or []
                    place_parts = []
                    for office in offices:
                        if isinstance(office, dict):
                            name = str(office.get("name") or "").strip()
                            loc_data = office.get("location")
                            if isinstance(loc_data, dict):
                                loc_name = str(loc_data.get("name") or "").strip()
                            else:
                                loc_name = str(loc_data or "").strip()
                            parts = [p for p in [name, loc_name] if p]
                            if parts:
                                place_parts.append(", ".join(parts))
                    place = place_parts[0] if place_parts else "Remote"
                    company = (
                        str(item.get("company") or self.board_token).strip()
                        if item.get("company")
                        else self.board_token
                    )
                    metadata = item.get("metadata") or []
                    tags = []
                    if isinstance(metadata, list):
                        for m in metadata:
                            if isinstance(m, dict):
                                val = str(m.get("value") or "").strip().lower()
                                if val and val not in ("", "none", "null"):
                                    tags.append(val)
                    departments = item.get("departments") or []
                    for dept in departments:
                        if isinstance(dept, dict):
                            dname = str(dept.get("name") or "").strip().lower()
                            if dname:
                                tags.append(dname)
                    desc = str(item.get("content") or "")
                    hay = f"{title} {company} {place} {' '.join(tags)} {desc}".lower()
                    if q and q not in hay:
                        continue
                    if loc and loc not in place.lower():
                        continue
                    raw_id = str(item.get("id") or title)
                    digest = hashlib.sha1(f"{self.name}:{raw_id}".encode()).hexdigest()[:12]
                    absolute_url = str(item.get("absolute_url") or "")
                    jobs.append(
                        JobPosting(
                            id=f"greenhouse-{digest}",
                            source=self.name,
                            title=title,
                            company=company,
                            location=place,
                            url=absolute_url,
                            description=desc[:4000],
                            tags=list(set(tags))[:20],
                            remote="remote" in place.lower(),
                            raw={"greenhouse_id": raw_id, "board_token": self.board_token},
                        )
                    )
                    if len(jobs) >= limit:
                        break
                meta = payload.get("meta")
                page_count = 1
                if isinstance(meta, dict):
                    page_count = int(meta.get("page_count", 1))
                if page >= page_count:
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
                    id=f"greenhouse-{digest}",
                    source=self.name,
                    title=title,
                    company=company,
                    location=place,
                    url=url,
                    description=f"{title} at {company} (offline Greenhouse sample).",
                    tags=tags,
                    remote="remote" in place.lower(),
                    raw={"offline": True, "board_token": self.board_token},
                )
            )
            if len(out) >= limit:
                break
        return out
