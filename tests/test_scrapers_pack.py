"""Tests for scraper pack #22 (bounties #5, #6, #7, #8, #9, #11, #16, #17)."""

from nerajob.scrapers.registry import available_scrapers, get_scraper


# ── Himalayas ─────────────────────────────────────────────────────────────


def test_himalayas_registered() -> None:
    assert "himalayas" in available_scrapers()


def test_himalayas_offline(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_HIMALAYAS_OFFLINE", "1")
    jobs = get_scraper("himalayas").search("python", limit=5)
    assert len(jobs) >= 1
    assert all(j.source == "himalayas" for j in jobs)


def test_himalayas_offline_query_filter(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_HIMALAYAS_OFFLINE", "1")
    jobs = get_scraper("himalayas").search("react", limit=5)
    assert len(jobs) >= 1
    assert all("react" in j.title.lower() or "react" in " ".join(j.tags) for j in jobs)


# ── Findwork ──────────────────────────────────────────────────────────────


def test_findwork_registered() -> None:
    assert "findwork" in available_scrapers()


def test_findwork_offline(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_FINDWORK_OFFLINE", "1")
    jobs = get_scraper("findwork").search("python", limit=5)
    assert len(jobs) >= 1
    assert all(j.source == "findwork" for j in jobs)


def test_findwork_offline_no_match(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_FINDWORK_OFFLINE", "1")
    jobs = get_scraper("findwork").search("zzzznotexist", limit=5)
    assert len(jobs) == 0


# ── Adzuna ────────────────────────────────────────────────────────────────


def test_adzuna_registered() -> None:
    assert "adzuna" in available_scrapers()


def test_adzuna_offline(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_ADZUNA_OFFLINE", "1")
    jobs = get_scraper("adzuna").search("python", limit=5)
    assert len(jobs) >= 1
    assert all(j.source == "adzuna" for j in jobs)


def test_adzuna_offline_country(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_ADZUNA_OFFLINE", "1")
    from nerajob.scrapers.adzuna import AdzunaScraper

    scraper = AdzunaScraper(country="de")
    jobs = scraper.search("python", limit=5)
    assert len(jobs) >= 1
    assert all(j.raw.get("country") == "de" for j in jobs)


# ── USAJobs ───────────────────────────────────────────────────────────────


def test_usajobs_registered() -> None:
    assert "usajobs" in available_scrapers()


def test_usajobs_offline(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_USAJOBS_OFFLINE", "1")
    jobs = get_scraper("usajobs").search("IT", limit=5)
    assert len(jobs) >= 1
    assert all(j.source == "usajobs" for j in jobs)


def test_usajobs_offline_no_credentials(monkeypatch) -> None:
    monkeypatch.delenv("USAJOBS_EMAIL", raising=False)
    monkeypatch.delenv("USAJOBS_API_KEY", raising=False)
    # Without credentials and without OFFLINE var, should return offline samples
    jobs = get_scraper("usajobs").search("python", limit=3)
    assert len(jobs) >= 1


# ── Reed ──────────────────────────────────────────────────────────────────


def test_reed_registered() -> None:
    assert "reed" in available_scrapers()


def test_reed_offline(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_REED_OFFLINE", "1")
    jobs = get_scraper("reed").search("python", limit=5)
    assert len(jobs) >= 1
    assert all(j.source == "reed" for j in jobs)


def test_reed_offline_location_filter(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_REED_OFFLINE", "1")
    jobs = get_scraper("reed").search("", location="Remote", limit=5)
    assert len(jobs) >= 1


# ── Greenhouse ────────────────────────────────────────────────────────────


def test_greenhouse_registered() -> None:
    assert "greenhouse" in available_scrapers()


def test_greenhouse_offline(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_GREENHOUSE_OFFLINE", "1")
    jobs = get_scraper("greenhouse").search("engineer", limit=5)
    assert len(jobs) >= 1
    assert all(j.source == "greenhouse" for j in jobs)


def test_greenhouse_offline_custom_board(monkeypatch) -> None:
    from nerajob.scrapers.greenhouse import GreenhouseScraper

    scraper = GreenhouseScraper(board_token="custom-board")
    monkeypatch.setenv("NERAJOB_GREENHOUSE_OFFLINE", "1")
    jobs = scraper.search("design", limit=5)
    assert len(jobs) >= 1
    assert all(j.raw.get("board_token") == "custom-board" for j in jobs)


# ── VietnamWorks ──────────────────────────────────────────────────────────


def test_vietnamworks_registered() -> None:
    assert "vietnamworks" in available_scrapers()


def test_vietnamworks_offline(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_VIETNAMWORKS_OFFLINE", "1")
    jobs = get_scraper("vietnamworks").search("python", limit=5)
    assert len(jobs) >= 1
    assert all(j.source == "vietnamworks" for j in jobs)


def test_vietnamworks_always_offline() -> None:
    jobs = get_scraper("vietnamworks").search("", limit=5)
    assert len(jobs) >= 1


# ── Arbeitnow EU ──────────────────────────────────────────────────────────


def test_arbeitnow_eu_registered() -> None:
    assert "arbeitnow_eu" in available_scrapers()


def test_arbeitnow_eu_offline(monkeypatch) -> None:
    monkeypatch.setenv("NERAJOB_ARBEITNOW_EU_OFFLINE", "1")
    jobs = get_scraper("arbeitnow_eu").search("python", limit=5)
    assert len(jobs) >= 1
    assert all(j.source == "arbeitnow_eu" for j in jobs)


def test_arbeitnow_eu_offline_country_filter(monkeypatch) -> None:
    from nerajob.scrapers.arbeitnow_eu import ArbeitnowEUScraper

    monkeypatch.setenv("NERAJOB_ARBEITNOW_EU_OFFLINE", "1")
    scraper = ArbeitnowEUScraper(country="germany")
    jobs = scraper.search("", limit=5)
    assert len(jobs) >= 1


# ── JobPosting validation common to all ───────────────────────────────────


def test_all_new_scrapers_offline_have_required_fields(monkeypatch) -> None:
    new_scrapers = [
        "himalayas",
        "findwork",
        "adzuna",
        "usajobs",
        "reed",
        "greenhouse",
        "vietnamworks",
        "arbeitnow_eu",
    ]
    for name in new_scrapers:
        scraper = get_scraper(name)
        env_name = f"NERAJOB_{name.upper()}_OFFLINE"
        monkeypatch.setenv(env_name, "1")
        jobs = scraper.search("", limit=3)
        assert len(jobs) >= 1, f"{name}: no offline jobs returned"
        for j in jobs:
            assert j.id, f"{name}: missing id"
            assert j.source == name, f"{name}: wrong source, got {j.source}"
            assert j.title, f"{name}: missing title"
            assert j.company, f"{name}: missing company"
