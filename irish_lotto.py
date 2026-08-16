#!/usr/bin/env python3
"""

================
Author: mrbacco04@gmail.com
Date: August 2026
License: MIT
================

Irish Lotto Tool

Scrapes recent Irish Lotto (main draw) results from lottery.ie and stores
them locally, then lets you generate a "hot/cold numbers" style prediction
based on how often each number has come up in the results you've collected.

IMPORTANT / HONEST DISCLAIMER
------------------------------
Irish Lotto draws are independent random events. The numbers drawn last
week have NO influence on the numbers drawn next week. Nothing -- not this
script, not any statistical model -- can improve your actual odds of
winning. The "predict" command here just tells you which numbers have
appeared most/least often in the data you've scraped so far. It's a fun
way to look at the data, not a real forecasting tool. Treat it as
entertainment only, and play responsibly.

USAGE
-----
    python irish_lotto.py scrape                # fetch latest results, save locally
    python irish_lotto.py stats                 # show frequency breakdown
    python irish_lotto.py predict                # suggest 6 numbers from hot numbers
    python irish_lotto.py predict --cold         # suggest 6 numbers from cold numbers
    python irish_lotto.py predict --weighted     # suggest 6 numbers, frequency-weighted random pick
    python irish_lotto.py list                  # show all draws currently stored

DATA FILE
---------
Results are stored in `lotto_results.json` in the same directory as this
script, so re-running `scrape` accumulates history over time instead of
losing it between runs.
"""

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup

DATA_FILE = Path(__file__).parent / "lotto_results.json"
HISTORY_URL = "https://www.lottery.ie/results/lotto/history"

# Irish Lotto: 6 main numbers from 1-47, plus a bonus number from 1-47
NUMBER_RANGE = range(1, 48)

HEADERS = {
    # A normal browser UA so the request isn't trivially blocked.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

DATE_RE = re.compile(r"\b([A-Z][a-z]{2} \d{2}/\d{2}/\d{2})\b")
# Matches the *main* Lotto jackpot block only (not the Plus 1 / Plus 2
# "Top prize" blocks, which use different wording).
DRAW_RE = re.compile(
    r"Jackpot\s*€\s*([\d,]+)\s*Winning numbers\s*"
    r"(\d{1,2})\D+(\d{1,2})\D+(\d{1,2})\D+(\d{1,2})\D+(\d{1,2})\D+(\d{1,2})\s*"
    r"Bonus\s*(\d{1,2})",
    re.IGNORECASE,
)


def fetch_page(url: str = HISTORY_URL) -> str:
    """Download the raw HTML of the results history page."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_draws(html: str):
    """
    Parse draw results out of the page's visible text.

    We deliberately parse the rendered text (not brittle CSS class names,
    which change often on marketing sites) by looking for the same
    labelled structure the page displays: a date heading, then
    "Jackpot", an amount, "Winning numbers", six numbers, and "Bonus".
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")

    # Split the page into per-draw-date chunks.
    date_matches = list(DATE_RE.finditer(text))
    draws = []
    for i, m in enumerate(date_matches):
        start = m.end()
        end = date_matches[i + 1].start() if i + 1 < len(date_matches) else len(text)
        chunk = text[start:end]

        draw_match = DRAW_RE.search(chunk)
        if not draw_match:
            continue  # page layout changed, or no main-draw data in this chunk

        jackpot_raw, *nums, bonus = draw_match.groups()
        try:
            date_obj = datetime.strptime(m.group(1), "%a %d/%m/%y")
        except ValueError:
            continue

        draws.append(
            {
                "date": date_obj.strftime("%Y-%m-%d"),
                "jackpot": int(jackpot_raw.replace(",", "")),
                "numbers": sorted(int(n) for n in nums),
                "bonus": int(bonus),
            }
        )
    return draws


def load_stored():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []


def save_stored(draws):
    with open(DATA_FILE, "w") as f:
        json.dump(draws, f, indent=2)


def merge_draws(existing, new):
    """Merge new draws into existing, deduplicating by date."""
    by_date = {d["date"]: d for d in existing}
    added = 0
    for d in new:
        if d["date"] not in by_date:
            added += 1
        by_date[d["date"]] = d
    merged = sorted(by_date.values(), key=lambda d: d["date"], reverse=True)
    return merged, added


def cmd_scrape(args):
    print(f"Fetching {HISTORY_URL} ...")
    try:
        html = fetch_page()
    except requests.RequestException as e:
        print(f"Error fetching page: {e}", file=sys.stderr)
        sys.exit(1)

    new_draws = parse_draws(html)
    if not new_draws:
        print(
            "No draws could be parsed. lottery.ie may have changed its page "
            "layout -- you may need to update the DRAW_RE / DATE_RE patterns "
            "in this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    existing = load_stored()
    merged, added = merge_draws(existing, new_draws)
    save_stored(merged)

    print(f"Parsed {len(new_draws)} draws from the page.")
    print(f"Added {added} new draw(s). Total stored: {len(merged)}.")
    print(
        "Note: lottery.ie only shows recent draws by default on this page "
        "(older results need clicking 'Load more', which this simple "
        "scraper doesn't automate). Run `scrape` periodically to build up "
        "history over time."
    )


def cmd_list(args):
    draws = load_stored()
    if not draws:
        print("No results stored yet. Run `scrape` first.")
        return
    for d in draws:
        nums = " ".join(f"{n:2d}" for n in d["numbers"])
        print(f"{d['date']}  Numbers: {nums}  Bonus: {d['bonus']:2d}  Jackpot: €{d['jackpot']:,}")


def compute_frequencies(draws):
    main_counter = Counter()
    bonus_counter = Counter()
    for d in draws:
        main_counter.update(d["numbers"])
        bonus_counter.update([d["bonus"]])
    return main_counter, bonus_counter


def cmd_stats(args):
    draws = load_stored()
    if not draws:
        print("No results stored yet. Run `scrape` first.")
        return

    main_counter, bonus_counter = compute_frequencies(draws)
    print(f"Based on {len(draws)} stored draws:\n")

    print("Most frequent main numbers ('hot'):")
    for num, count in main_counter.most_common(10):
        print(f"  {num:2d} -- drawn {count} time(s)")

    print("\nLeast frequent main numbers ('cold'):")
    least_common = sorted(main_counter.items(), key=lambda x: x[1])[:10]
    for num, count in least_common:
        print(f"  {num:2d} -- drawn {count} time(s)")

    never_drawn = [n for n in NUMBER_RANGE if n not in main_counter]
    if never_drawn:
        print(f"\nNumbers never seen in stored data: {never_drawn}")

    print("\nMost frequent bonus numbers:")
    for num, count in bonus_counter.most_common(5):
        print(f"  {num:2d} -- drawn {count} time(s)")


def cmd_predict(args):
    draws = load_stored()
    if not draws:
        print("No results stored yet. Run `scrape` first.")
        return

    main_counter, bonus_counter = compute_frequencies(draws)

    print(
        "Reminder: Lotto draws are random and independent -- this is a "
        "statistical curiosity based on past frequency, not a real "
        "forecast, and it does not improve your odds of winning.\n"
    )

    if args.cold:
        # Fill in unseen numbers as "coldest of all" first
        all_counts = {n: main_counter.get(n, 0) for n in NUMBER_RANGE}
        picks = sorted(all_counts.items(), key=lambda x: x[1])[:6]
        picks = sorted(n for n, _ in picks)
        print(f"Cold-number pick (least frequent in stored data): {picks}")

    elif args.weighted:
        numbers = list(NUMBER_RANGE)
        # add +1 so numbers with 0 recorded appearances can still be picked
        weights = [main_counter.get(n, 0) + 1 for n in numbers]
        picks = sorted(random.sample(
            population=numbers,
            k=6,
        )) if len(set(weights)) == 1 else sorted(
            _weighted_sample_without_replacement(numbers, weights, 6)
        )
        print(f"Frequency-weighted random pick: {picks}")

    else:
        picks = sorted(n for n, _ in main_counter.most_common(6))
        print(f"Hot-number pick (most frequent in stored data): {picks}")

    top_bonus = bonus_counter.most_common(1)
    if top_bonus:
        print(f"Most frequent bonus number: {top_bonus[0][0]}")


def _weighted_sample_without_replacement(population, weights, k):
    """Simple weighted sampling without replacement."""
    pool = list(zip(population, weights))
    chosen = []
    for _ in range(k):
        total = sum(w for _, w in pool)
        r = random.uniform(0, total)
        upto = 0
        for i, (item, w) in enumerate(pool):
            upto += w
            if upto >= r:
                chosen.append(item)
                pool.pop(i)
                break
    return chosen


def main():
    parser = argparse.ArgumentParser(description="Irish Lotto scraper & number-frequency tool")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scrape", help="Fetch latest results from lottery.ie and save locally")
    sub.add_parser("list", help="List all stored draws")
    sub.add_parser("stats", help="Show hot/cold number frequency breakdown")

    predict_parser = sub.add_parser("predict", help="Suggest 6 numbers based on stored frequency data")
    group = predict_parser.add_mutually_exclusive_group()
    group.add_argument("--cold", action="store_true", help="Pick the least frequent numbers instead of the most frequent")
    group.add_argument("--weighted", action="store_true", help="Randomly pick numbers, weighted by frequency")

    args = parser.parse_args()

    commands = {
        "scrape": cmd_scrape,
        "list": cmd_list,
        "stats": cmd_stats,
        "predict": cmd_predict,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
