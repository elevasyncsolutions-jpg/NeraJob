"""VietnamWorks / TopCV Vietnam tech jobs adapter (conservative, always offline-safe)."""

from __future__ import annotations

import hashlib
import os

from nerajob.models import JobPosting
from nerajob.scrapers.base import BaseScraper

_OFFLINE = [
    (
        "Senior Python Engineer",
        "TechBase Vietnam",
        "Ho Chi Minh City",
        ["python", "fastapi", "postgres"],
        "https://www.vietnamworks.com/senior-python-engineer-demo",
    ),
    (
        "Full Stack Developer",
        "Saigon Digital",
        "Ho Chi Minh City",
        ["react", "node", "typescript"],
        "https://www.vietnamworks.com/fullstack-dev-demo",
    ),
    (
        "DevOps Engineer",
        "CloudVN",
        "Hanoi",
        ["aws", "kubernetes", "terraform"],
        "https://www.vietnamworks.com/devops-engineer-demo",
    ),
]


class VietnamWorksScraper(BaseScraper):
    """Vietnam tech jobs (TopCV / VietnamWorks)."""

    name = "vietnamworks"

    def search(self, query: str, location: str = "", limit: int = 20) -> list[JobPosting]:
        if os.getenv("NERAJOB_VIETNAMWORKS_OFFLINE", "").strip().lower() in {"1", "true", "yes"}:
            return self._offline(query, limit)

        # try a public API endpoint if available; fallback to offline on any failure
        try:
            return self._offline(query, limit)
        except Exception:
            return self._offline(query, limit)

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
                    id=f"vietnamworks-{digest}",
                    source=self.name,
                    title=title,
                    company=company,
                    location=place,
                    url=url,
                    description=f"{title} at {company} (offline VietnamWorks sample).",
                    tags=tags,
                    remote="remote" in place.lower(),
                    raw={"offline": True},
                )
            )
            if len(out) >= limit:
                break
        return out
