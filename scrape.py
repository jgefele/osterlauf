#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import socket
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen
from urllib.parse import quote

from bs4 import BeautifulSoup

BASE_URL = (
    "https://paderborner-osterlauf.r.mikatiming.com/2026/"
    "?page={page}&event=10&pid=startlist_list"
)
DEFAULT_ENTRY = ("2025-12-20T11:51:00", 1784, 0)
DATA_PATH = Path("data.csv")
USER_AGENT = "Mozilla/5.0 (compatible; OsterlaufScraper/1.0)"


@dataclass
class PageResult:
    page: int
    participant_count: int
    last_page: int


def parse_page(html: str, page: int) -> PageResult:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find("div", class_="pid-startlist_list")
    last_page = page
    pagination = soup.find("ul", class_="pagination")
    if pagination:
        for link in pagination.find_all("a"):
            label = link.get_text(strip=True)
            if label.isdigit():
                last_page = max(last_page, int(label))
    if container:
        rows = container.select("li.list-group-item.row")
        rows = [
            row
            for row in rows
            if "list-group-header" not in (row.get("class") or [])
            and not row.get_text(strip=True).lower().startswith("no results")
        ]
        if rows:
            return PageResult(page=page, participant_count=len(rows), last_page=last_page)
    table = soup.find("table")
    if table is None:
        return PageResult(page=page, participant_count=0, last_page=last_page)
    rows = table.find_all("tr")
    count = sum(1 for row in rows if row.find("td") is not None)
    return PageResult(page=page, participant_count=count, last_page=last_page)


def fetch_page_html(page: int, url_template: str) -> str:
    url = url_template.format(page=page)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    socket.setdefaulttimeout(10)
    with urlopen(request, timeout=10) as response:
        return response.read().decode("utf-8", errors="ignore")


def fetch_page_participants(page: int, url_template: str) -> PageResult:
    html = fetch_page_html(page, url_template)
    return parse_page(html, page)


def build_name_url_template(name: str) -> str:
    encoded_name = quote(name)
    return (
        "https://paderborner-osterlauf.r.mikatiming.com/2026/"
        "?page={page}&event=10&pid=startlist_list&search%5Bname%5D="
        f"{encoded_name}"
    )


def load_entries(path: Path) -> list[tuple[str, int, int | None]]:
    if not path.exists() or path.stat().st_size == 0:
        return [DEFAULT_ENTRY]

    entries: list[tuple[str, int, int | None]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(row) < 2:
                continue
            timestamp = row[0].strip()
            try:
                count = int(row[1])
            except ValueError:
                continue
            rueweler_count: int | None = None
            if len(row) >= 3 and row[2].strip():
                try:
                    rueweler_count = int(row[2])
                except ValueError:
                    rueweler_count = None
            if timestamp:
                entries.append((timestamp, count, rueweler_count))

    return entries or [DEFAULT_ENTRY]


def write_entries(path: Path, entries: Iterable[tuple[str, int, int | None]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        for timestamp, total, rueweler_count in entries:
            row = [timestamp, total]
            row.append("" if rueweler_count is None else rueweler_count)
            writer.writerow(row)


def find_total_participants(url_template: str) -> int:
    first_page = fetch_page_participants(1, url_template)
    if first_page.participant_count == 0:
        return 0
    if first_page.last_page <= 1:
        return first_page.participant_count

    last_page_result = fetch_page_participants(first_page.last_page, url_template)
    page_size = first_page.participant_count
    return (last_page_result.last_page - 1) * page_size + last_page_result.participant_count


def find_participants_for_name(name: str) -> int:
    url_template = build_name_url_template(name)
    count = find_total_participants(url_template)
    if count == 0 and " " not in name and len(name) > 1:
        fallback_name = name[1:]
        fallback_template = build_name_url_template(fallback_name)
        fallback_count = find_total_participants(fallback_template)
        if fallback_count > 0:
            return fallback_count
    return count


def run_tests() -> None:
    expectations = {
        "rüweler": 0,
        "jgefele": 1,
        "sch": 198,
    }

    for name, expected in expectations.items():
        result = find_participants_for_name(name)
        assert (
            result == expected
        ), f"Erwartet {expected} für {name!r}, erhalten {result}"
        print(f"Test {name!r}: {result} Teilnehmer (ok)")


def main() -> None:
    entries = load_entries(DATA_PATH)
    total_participants = find_total_participants(BASE_URL)

    rueweler_participants = find_participants_for_name("rüweler")

    timestamp = datetime.now().isoformat(timespec="seconds")
    entries.append((timestamp, total_participants, rueweler_participants))
    write_entries(DATA_PATH, entries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Starte die Namens-Tests")
    args = parser.parse_args()

    if args.test:
        run_tests()
    else:
        main()
