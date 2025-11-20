"""Scrape WBF tournament boards + results and emit JSON on stdout.

Designed to be spawned from a NestJS backend via child_process.

Usage:
    python main.py --url <wbf-round-url>

Stdout (single JSON document):
    {
      "source": "<url>",
      "boards": [
        {
          "number": 1,
          "dealer": "N",
          "vulnerability": "None",
          "hands": {
            "N": {"S": "AKQ72", "H": "T93", "D": "K54", "C": "A8"},
            "E": {...}, "S": {...}, "W": {...}
          },
          "lin": "qx|o1|md|3SAKQ72HT93DK54CA8,...|rh||ah|Board 1|sv|0|pg||",
          "pbn": "[Board \"1\"]\n[Dealer \"N\"]\n[Vulnerable \"None\"]\n[Deal \"N:...\"]",
          "results": [
            {
              "table": "1", "home_team": "...", "visiting_team": "...",
              "room": "Open", "contract": "4S", "declarer": "N",
              "lead": "HA", "tricks": "10", "ns": 620, "ew": -620,
              "home_result": "...", "vis_result": "..."
            }
          ]
        }
      ]
    }

On error: exits non-zero with `{"error": "..."}` on stderr.
"""
import argparse
import json
import sys
from typing import List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SCORE_START_INDEX = 13
DECLARER_VALUES = ("N", "E", "S", "W")
SUIT_MAP = {"♠": "S", "♥": "H", "♦": "D", "♣": "C"}
MIN_CELLS_FOR_SCORE = 100

VULNERABILITY_MAP = {
    "None Vulnerable": "None",
    "N-S Vulnerable": "NS",
    "E-W Vulnerable": "EW",
    "All Vulnerable": "All",
}

# LIN encodings (BBO format): dealer 1=S 2=W 3=N 4=E, vul 0/N/E/B
DEALER_LIN = {"N": "3", "E": "4", "S": "1", "W": "2"}
VUL_LIN = {"None": "0", "NS": "N", "EW": "E", "All": "B"}


def fetch_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def get_unique_board_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    seen, links = set(), []
    for a in soup.find_all("a", href=True):
        if "Boardacross.asp" not in a["href"]:
            continue
        full = urljoin(base_url, a["href"])
        if full not in seen:
            seen.add(full)
            links.append(full)
    return links


def extract_board_meta(text: str) -> Tuple[Optional[int], str, str]:
    """Parse 'Board N. Dealer X. Y Vulnerable' header text."""
    parts = text.split(".")
    if len(parts) < 3:
        return None, "", ""
    try:
        number = int(parts[0].replace("Board", "").strip())
    except ValueError:
        number = None
    dealer = parts[1].replace("Dealer", "").strip()[:1].upper()
    vul_raw = parts[2].strip()
    return number, dealer, VULNERABILITY_MAP.get(vul_raw, vul_raw)


def extract_hand(td) -> dict:
    """Extract a hand as {'S': 'AKQ72', 'H': 'T93', 'D': 'K54', 'C': 'A8'}."""
    hand = {"S": "", "H": "", "D": "", "C": ""}
    current_suit = None
    for elem in td.descendants:
        if elem.name:
            continue
        for char in elem.strip():
            if char in SUIT_MAP:
                current_suit = SUIT_MAP[char]
            elif current_suit and char.upper() in "AKQJT98765432":
                hand[current_suit] += char.upper()
    return hand


def find_score_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        first_row = table.find("tr")
        if first_row and "Table" in first_row.get_text():
            return table
    return None


def _to_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_first_result(cells: List[str], start_idx: int) -> Tuple[dict, int]:
    idx = start_idx + 5
    while idx < len(cells) and cells[idx] not in DECLARER_VALUES:
        idx += 1
    return {
        "table": cells[start_idx],
        "home_team": cells[start_idx + 1],
        "visiting_team": cells[start_idx + 2],
        "room": cells[start_idx + 3],
        "contract": cells[start_idx + 4][:2],
        "declarer": cells[idx],
        "lead": cells[idx + 1],
        "tricks": cells[idx + 2],
        "ns": _to_int(cells[idx + 3]),
        "ew": _to_int(cells[idx + 4]),
        "home_result": cells[idx + 5],
        "vis_result": cells[idx + 6],
    }, idx + 7


def _parse_second_result(cells: List[str], start_idx: int, first: dict) -> Tuple[dict, int]:
    idx = start_idx + 2
    while idx < len(cells) and cells[idx] not in DECLARER_VALUES:
        idx += 1
    return {
        "table": first["table"],
        "home_team": first["home_team"],
        "visiting_team": first["visiting_team"],
        "room": cells[start_idx],
        "contract": cells[start_idx + 1][:2],
        "declarer": cells[idx],
        "lead": cells[idx + 1],
        "tricks": cells[idx + 2],
        "ns": _to_int(cells[idx + 3]),
        "ew": _to_int(cells[idx + 4]),
        "home_result": first["home_result"],
        "vis_result": first["vis_result"],
    }, idx + 5


def extract_results(soup: BeautifulSoup) -> List[dict]:
    table = find_score_table(soup)
    if not table:
        return []

    out: List[dict] = []
    for tr in table.find_all("tr")[2:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < MIN_CELLS_FOR_SCORE:
            continue

        idx = SCORE_START_INDEX
        while idx < len(cells) - 1:
            first, idx = _parse_first_result(cells, idx)
            out.append(first)
            if idx >= len(cells) - 5:
                break
            second, idx = _parse_second_result(cells, idx, first)
            out.append(second)
    return out


def _hand_to_lin(hand: dict) -> str:
    return f"S{hand['S']}H{hand['H']}D{hand['D']}C{hand['C']}"


def _hand_to_pbn(hand: dict) -> str:
    return f"{hand['S']}.{hand['H']}.{hand['D']}.{hand['C']}"


def to_lin(number, dealer: str, vulnerability: str, hands: dict) -> str:
    """Build a single-board LIN string (BBO format)."""
    d = DEALER_LIN.get(dealer, "0")
    v = VUL_LIN.get(vulnerability, "0")
    # LIN md| field lists hands in fixed S,W,N,E order regardless of dealer
    s, w, n, e = (_hand_to_lin(hands[k]) for k in ("S", "W", "N", "E"))
    return f"qx|o{number}|md|{d}{s},{w},{n},{e}|rh||ah|Board {number}|sv|{v}|pg||"


def to_pbn(number, dealer: str, vulnerability: str, hands: dict) -> str:
    """Build the minimum PBN tags for a single board."""
    deal = " ".join(_hand_to_pbn(hands[seat]) for seat in ("N", "E", "S", "W"))
    return (
        f'[Board "{number}"]\n'
        f'[Dealer "{dealer}"]\n'
        f'[Vulnerable "{vulnerability}"]\n'
        f'[Deal "N:{deal}"]'
    )


def scrape_board(link: str) -> Optional[dict]:
    soup = fetch_soup(link)

    info_td = soup.find("td", class_="BrdDispl", colspan="3")
    if not info_td:
        return None
    number, dealer, vul = extract_board_meta(info_td.get_text(strip=True))

    hand_tds = [td for td in soup.find_all("td", class_="BrdDispl") if td is not info_td]
    if len(hand_tds) < 4:
        return None

    hands = {
        "N": extract_hand(hand_tds[0]),
        "W": extract_hand(hand_tds[1]),
        "E": extract_hand(hand_tds[2]),
        "S": extract_hand(hand_tds[3]),
    }
    return {
        "number": number,
        "dealer": dealer,
        "vulnerability": vul,
        "hands": hands,
        "lin": to_lin(number, dealer, vul, hands),
        "pbn": to_pbn(number, dealer, vul, hands),
        "results": extract_results(soup),
    }


def scrape_tournament(url: str) -> dict:
    main_soup = fetch_soup(url)
    board_links = get_unique_board_links(main_soup, url)
    boards = [b for b in (scrape_board(link) for link in board_links) if b is not None]
    return {"source": url, "boards": boards}


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape WBF tournament boards + results as JSON")
    parser.add_argument("--url", required=True, help="WBF tournament round URL")
    args = parser.parse_args()

    try:
        data = scrape_tournament(args.url)
    except Exception as exc:
        json.dump({"error": f"{type(exc).__name__}: {exc}"}, sys.stderr)
        sys.stderr.write("\n")
        sys.exit(1)

    json.dump(data, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
