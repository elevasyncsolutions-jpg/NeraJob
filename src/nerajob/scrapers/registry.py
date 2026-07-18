from __future__ import annotations

import os

from nerajob.scrapers.arbeitnow import ArbeitnowScraper
from nerajob.scrapers.arbeitnow_eu import ArbeitnowEUScraper
from nerajob.scrapers.adzuna import AdzunaScraper
from nerajob.scrapers.ashby import AshbyScraper
from nerajob.scrapers.base import BaseScraper
from nerajob.scrapers.findwork import FindworkScraper
from nerajob.scrapers.greenhouse import GreenhouseScraper
from nerajob.scrapers.himalayas import HimalayasScraper
from nerajob.scrapers.jobicy import JobicyScraper
from nerajob.scrapers.lever import LeverScraper
from nerajob.scrapers.reed import ReedScraper
from nerajob.scrapers.remoteok import RemoteOKScraper
from nerajob.scrapers.remotive import RemotiveScraper
from nerajob.scrapers.sample import SampleScraper
from nerajob.scrapers.smartrecruiters import SmartRecruitersScraper
from nerajob.scrapers.themuse import TheMuseScraper
from nerajob.scrapers.usajobs import USAJobsScraper
from nerajob.scrapers.vietnamworks import VietnamWorksScraper
from nerajob.scrapers.weworkremotely import WeWorkRemotelyScraper


def available_scrapers() -> dict[str, BaseScraper]:
    """
    Built-in scrapers.

    Lever / Ashby board IDs (optional):
      NERAJOB_LEVER_BOARD   e.g. company slug for api.lever.co
      NERAJOB_ASHBY_BOARD   e.g. board id for api.ashbyhq.com
    Without env, those adapters use offline sample postings (tests/demos).

    Remotive:      live public API; set NERAJOB_REMOTIVE_OFFLINE=1 to force offline samples.
    Arbeitnow:     live public API; set NERAJOB_ARBEITNOW_OFFLINE=1 for offline samples.
    Jobicy:        live public API; set NERAJOB_JOBICY_OFFLINE=1 for offline samples.
    We Work Remotely: RSS feed; set NERAJOB_WWR_OFFLINE=1 for offline samples.
    SmartRecruiters: set NERAJOB_SMARTRECRUITERS_COMPANIES to comma-separated company IDs.

    Himalayas (bounty #5):
      Public API at https://himalayas.app/jobs/api, no key needed.
      Set NERAJOB_HIMALAYAS_OFFLINE=1 for offline samples.

    Findwork (bounty #6):
      API at https://findwork.dev/api/jobs/, needs FINDWORK_API_KEY env.
      Set NERAJOB_FINDWORK_OFFLINE=1 for offline samples.

    Adzuna (bounty #7):
      API at https://api.adzuna.com/v1/api/jobs/{country}/search/{page}.
      Needs ADZUNA_APP_ID and ADZUNA_API_KEY env vars.
      Set NERAJOB_ADZUNA_OFFLINE=1 for offline samples.

    USAJobs (bounty #8):
      API at https://data.usajobs.gov/api/search.
      Needs USAJOBS_EMAIL and USAJOBS_API_KEY env vars.
      Set NERAJOB_USAJOBS_OFFLINE=1 for offline samples.

    Reed (bounty #9):
      API at https://www.reed.co.uk/api/1.0/search.
      Needs REED_API_KEY env var.
      Set NERAJOB_REED_OFFLINE=1 for offline samples.

    Greenhouse (bounty #11):
      API at https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs.
      Set NERAJOB_GREENHOUSE_BOARD for board token (default: mergeos).
      Set NERAJOB_GREENHOUSE_OFFLINE=1 for offline samples.

    VietnamWorks (bounty #17):
      Conservative scraper that always returns offline samples.
      Set NERAJOB_VIETNAMWORKS_OFFLINE=1 to force (already default).

    Arbeitnow EU (bounty #16):
      EU-filtered variant of the Arbeitnow API.
      Set NERAJOB_ARBEITNOW_EU_OFFLINE=1 for offline samples.
    """
    scrapers: list[BaseScraper] = [
        SampleScraper(),
        RemoteOKScraper(),
        RemotiveScraper(),
        ArbeitnowScraper(),
        ArbeitnowEUScraper(),
        JobicyScraper(),
        TheMuseScraper(),
        WeWorkRemotelyScraper(),
        LeverScraper(board_name=os.getenv("NERAJOB_LEVER_BOARD") or None),
        AshbyScraper(board_id=os.getenv("NERAJOB_ASHBY_BOARD") or None),
        SmartRecruitersScraper(),
        HimalayasScraper(),
        FindworkScraper(),
        AdzunaScraper(),
        USAJobsScraper(),
        ReedScraper(),
        GreenhouseScraper(),
        VietnamWorksScraper(),
    ]
    return {s.name: s for s in scrapers}


def get_scraper(name: str) -> BaseScraper:
    scrapers = available_scrapers()
    if name not in scrapers:
        known = ", ".join(sorted(scrapers))
        raise KeyError(f"Unknown scraper {name!r}. Known: {known}")
    return scrapers[name]
