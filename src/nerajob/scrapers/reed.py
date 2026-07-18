"""Reed.co.uk Jobs API adapter with offline fallback."""

from __future__ import annotations

import asyncio
import hashlib
import os

from nerajob.http import ScraperHTTPClient
from nerajob.models import JobPosting
from nerajob.scrapers.base import BaseScraper

_OFFLINE = [
    (
        "Python Developer",
        "Reed Demo Ltd",
        "London, UK",
        ["python", "django", "sql"],
        "https://www.reed.co.uk/jobs/python-developer-demo",
    ),
    (
        "Frontend Developer",
        "Digital Craft",
        "Manchester, UK",
        ["javascript", "react", "html"],
        "https://www.reed.co.uk/jobs/frontend-dev-demo",
    ),
    (
        "DevOps Engineer",
        "CloudNine UK",
        "Remote",
        ["aws", "kubernetes", "docker"],
        "https://www.reed.co.uk/jobs/devops-demo",
    ),
]


class ReedScraper(BaseScraper):
    """https://www.reed.co.uk/api/1.0/search"""

    name = "reed"
    API_URL = "https://www.reed.co.uk/api/1.0/search"

    def search(self, query: str, location: str = "", limit: int = 20) -> list[JobPosting]:
        if os.getenv("NERAJOB_REED_OFFLINE", "").strip().lower() in {"1", "true", "yes"}:
            return self._offline(query, limit)
        api_key = os.getenv("REED_API_KEY", "")
        if not api_key:
            return self._offline(query, limit)
        try:
            return asyncio.run(self._async_search(query, location, limit, api_key))
        except Exception:
            return self._offline(query, limit)

    async def _async_search(
        self, query: str, location: str, limit: int, api_key: str
    ) -> list[JobPosting]:
        client = ScraperHTTPClient()
        jobs: list[JobPosting] = []
        q = query.strip().lower()
        loc = location.strip().lower()
        page = 1
        try:
            while len(jobs) < limit:
                params: dict[str, object] = {
                    "pagesize": min(limit, 100),
                    "page": page,
                }
                if q:
                    params["keywords"] = q
                if loc:
                    params["locationName"] = loc
                resp = await client.get(
                    self.API_URL,
                    params=params,
                    auth=(api_key, ""),
                    headers={"Accept": "application/json"},
                )
                payload = resp.json()
                results = payload.get("results") if isinstance(payload, dict) else None
                if not isinstance(results, list) or not results:
                    break
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get("jobTitle") or item.get("title") or "").strip()
                    company = str(item.get("employerName") or "").strip()
                    if not title:
                        continue
                    tags = []
                    for key in ("jobCategory", "industry"):
                        val = item.get(key)
                        if val:
                            tags.append(str(val).strip().lower())
                    place = str(item.get("locationName") or "Remote")
                    desc = str(item.get("jobDescription") or "")
                    hay = f"{title} {company} {place} {' '.join(tags)} {desc}".lower()
                    if q and q not in hay:
                        continue
                    if loc and loc not in place.lower():
                        continue
                    raw_id = str(item.get("jobId") or title)
                    digest = hashlib.sha1(f"{self.name}:{raw_id}".encode()).hexdigest()[:12]
                    salary_str = ""
                    min_sal = item.get("minimumSalary")
                    max_sal = item.get("maximumSalary")
                    if min_sal is not None and max_sal is not None:
                        salary_str = f"{min_sal}-{max_sal}"
                    elif min_sal is not None:
                        salary_str = str(min_sal)
                    elif max_sal is not None:
                        salary_str = str(max_sal)
                    jobs.append(
                        JobPosting(
                            id=f"reed-{digest}",
                            source=self.name,
                            title=title,
                            company=company or "Unknown",
                            location=place,
                            url=str(item.get("jobUrl") or ""),
                            description=desc[:4000],
                            tags=tags[:20],
                            salary=salary_str,
                            remote="remote" in place.lower(),
                            raw={"reed_id": raw_id},
                        )
                    )
                    if len(jobs) >= limit:
                        break
                total = payload.get("totalResults", 0)
                if not isinstance(total, (int, float)):
                    total = 0
                if page * int(params.get("pagesize", 100)) >= int(total):
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
                    id=f"reed-{digest}",
                    source=self.name,
                    title=title,
                    company=company,
                    location=place,
                    url=url,
                    description=f"{title} at {company} (offline Reed sample).",
                    tags=tags,
                    remote="remote" in place.lower(),
                    raw={"offline": True},
                )
            )
            if len(out) >= limit:
                break
        return out
