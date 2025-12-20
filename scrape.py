#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import socket
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE_URL = (
    "https://paderborner-osterlauf.r.mikatiming.com/2026/"
    "?page={page}&event=10&pid=startlist_list"
)
DEFAULT_ENTRY = ("2025-12-20T11:51:00", 1784)
DATA_PATH = Path("data.csv")
USER_AGENT = "Mozilla/5.0 (compatible; OsterlaufScraper/1.0)"


@dataclass
class PageResult:
    page: int
    participant_count: int


def parse_participant_count(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find("div", class_="pid-startlist_list")
    if container:
        rows = container.select("li.list-group-item.row")
        rows = [
            row
            for row in rows
            if "list-group-header" not in (row.get("class") or [])
        ]
        if rows:
            return len(rows)
    table = soup.find("table")
    if table is None:
        return 0
    rows = table.find_all("tr")
    return sum(1 for row in rows if row.find("td") is not None)


def fetch_page_html(page: int) -> str:
    url = BASE_URL.format(page=page)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    socket.setdefaulttimeout(10)
    with urlopen(request, timeout=10) as response:
        return response.read().decode("utf-8", errors="ignore")


def fetch_page_participants(page: int) -> PageResult:
    html = fetch_page_html(page)
    count = parse_participant_count(html)
    return PageResult(page=page, participant_count=count)


def load_entries(path: Path) -> list[tuple[str, int]]:
    if not path.exists() or path.stat().st_size == 0:
        return [DEFAULT_ENTRY]

    entries: list[tuple[str, int]] = []
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
            if timestamp:
                entries.append((timestamp, count))

    return entries or [DEFAULT_ENTRY]


def write_entries(path: Path, entries: Iterable[tuple[str, int]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(entries)


def infer_start_page(last_count: int) -> int:
    if last_count <= 0:
        return 1
    return max(1, math.ceil(last_count / 25))


def find_total_participants(start_page: int) -> int:
    page = max(1, start_page)
    last_full_count: int | None = None

    while True:
        result = fetch_page_participants(page)
        count = result.participant_count
        if count == 0:
            if last_full_count is None:
                if page == 1:
                    return 0
                page -= 1
                continue
            return (page - 1) * 25 + last_full_count
        if count < 25:
            return (page - 1) * 25 + count
        last_full_count = count
        page += 1


def main() -> None:
    entries = load_entries(DATA_PATH)
    last_count = entries[-1][1]
    start_page = infer_start_page(last_count)
    total_participants = find_total_participants(start_page)
    assert total_participants >= last_count

    timestamp = datetime.now().isoformat(timespec="seconds")
    entries.append((timestamp, total_participants))
    write_entries(DATA_PATH, entries)


if __name__ == "__main__":
    main()
