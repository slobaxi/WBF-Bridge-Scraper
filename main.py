import requests
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional
import pandas as pd
from Score import Score

# ----------------------------
# CONFIG / CONSTANTS
# ----------------------------
MAIN_URL = "https://db.worldbridge.org/Repository/tourn/Herning.25/microSite/Asp/boardacrossfullround.asp?qtournid=2550&qround=1"
BASE_URL = "https://db.worldbridge.org/Repository/tourn/Herning.25/microSite/Asp/"
SCORE_START_INDEX = 13
DECLARER_VALUES = ('N', 'E', 'S', 'W')
SUIT_MAP = {"♠": "S", "♥": "H", "♦": "D", "♣": "C"}
MIN_CELLS_FOR_SCORE = 100

VULNERABILITY_MAP = {
    "None Vulnerable": "0",
    "N-S Vulnerable": "N",
    "E-W Vulnerable": "E",
    "All Vulnerable": "B"
}

DEALER_MAP = {"N": "3", "E": "4", "S": "1", "W": "2"}

# ----------------------------
# UTILITY FUNCTIONS
# ----------------------------
def fetch_soup(url: str) -> BeautifulSoup:
    """Fetches a URL and returns a BeautifulSoup object."""
    resp = requests.get(url)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def get_unique_board_links(soup: BeautifulSoup) -> List[Tuple[str, str]]:
    """Extract unique board links from the main page."""
    board_links = []
    for td in soup.find_all("td"):
        a_tag = td.find("a")
        if a_tag and "Boardacross.asp" in a_tag.get("href", ""):
            board_links.append((a_tag.get_text(strip=True), BASE_URL + a_tag["href"]))
    # Remove duplicates
    return list({link: number for number, link in board_links}.items())


def extract_dealer_vul(text: str) -> Tuple[str, str, str]:
    """Extracts board number, dealer, and vulnerability from text."""
    parts = text.split(".")
    if len(parts) < 3:
        return "0", "0", "0"
    board_number = parts[0].replace("Board", "").strip()
    dealer_full = parts[1].replace("Dealer", "").strip()
    dealer = dealer_full[0].upper()
    vul_text = parts[2].strip()
    vul_code = VULNERABILITY_MAP.get(vul_text, "0")
    dealer_code = DEALER_MAP.get(dealer, "0")
    return board_number, dealer_code, vul_code


def clean_cards(td) -> str:
    """Convert a card td to LIN-style string: S[spades]H[hearts]D[diamonds]C[clubs]"""
    hand = {"S": "", "H": "", "D": "", "C": ""}
    current_suit = None
    for elem in td.descendants:
        if elem.name:
            continue
        text = elem.strip()
        if not text:
            continue
        for char in text:
            if char in SUIT_MAP:
                current_suit = SUIT_MAP[char]
            elif current_suit and char.upper() in "AKQJT98765432":
                hand[current_suit] += char.upper()
    return f"S{hand['S']}H{hand['H']}D{hand['D']}C{hand['C']}"


def find_score_table(soup: BeautifulSoup) -> Optional[BeautifulSoup]:
    """Find the results table in a board page."""
    for table in soup.find_all("table"):
        first_row = table.find("tr")
        if first_row and "Table" in first_row.get_text():
            return table
    return None


def parse_score_row(cells: List[str], start_idx: int) -> Tuple[Score, int]:
    """Parse a single row of scores starting at start_idx. Returns Score and next index."""
    score = Score()
    score.Table = cells[start_idx]
    score.Home_Team = cells[start_idx + 1]
    score.Visiting_Team = cells[start_idx + 2]
    score.Room = cells[start_idx + 3]
    score.Contract = cells[start_idx + 4][:2]

    idx = start_idx + 5
    while cells[idx] not in DECLARER_VALUES:
        idx += 1

    score.Declarer = cells[idx]
    score.Lead = cells[idx + 1]
    score.Tricks = cells[idx + 2]
    score.NS = cells[idx + 3]
    score.EW = cells[idx + 4]
    score.Home_Result = cells[idx + 5]
    score.Vis_Result = cells[idx + 6]

    return score, idx + 7


def extract_scores(soup: BeautifulSoup) -> List[Score]:
    """Extract all scores from a board page."""
    table = find_score_table(soup)
    if not table:
        return []

    scores = []
    for tr in table.find_all("tr")[2:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < MIN_CELLS_FOR_SCORE:
            continue

        idx = SCORE_START_INDEX
        while idx < len(cells) - 1:
            # First score
            score_first, idx = parse_score_row(cells, idx)
            scores.append(score_first)

            # Second score
            if idx >= len(cells) - 5:
                break
            score_second = Score()
            score_second.Table = score_first.Table
            score_second.Home_Team = score_first.Home_Team
            score_second.Visiting_Team = score_first.Visiting_Team
            score_second.Room = cells[idx]
            score_second.Contract = cells[idx + 1][:2]

            tmp_idx = idx + 2
            while cells[tmp_idx] not in DECLARER_VALUES:
                tmp_idx += 1
            score_second.Declarer = cells[tmp_idx]
            score_second.Lead = cells[tmp_idx + 1]
            score_second.Tricks = cells[tmp_idx + 2]
            score_second.NS = cells[tmp_idx + 3]
            score_second.EW = cells[tmp_idx + 4]
            score_second.Home_Result = score_first.Home_Result
            score_second.Vis_Result = score_first.Vis_Result
            scores.append(score_second)

            idx = tmp_idx + 5

    return scores


def scores_to_excel(scores: List[Score], filename: str = "scores.xlsx") -> None:
    """Save list of Score objects to Excel."""
    rows = []
    for s in scores:
        rows.append({
            "BoardNumber": s.BoardNumber,
            "Table": s.Table,
            "Home_Team": s.Home_Team,
            "Visiting_Team": s.Visiting_Team,
            "Room": s.Room,
            "Contract": s.Contract,
            "Declarer": s.Declarer,
            "Lead": s.Lead,
            "Tricks": s.Tricks,
            "NS": s.NS,
            "EW": s.EW,
            "Home_Result": s.Home_Result,
            "Vis_Result": s.Vis_Result
        })
    pd.DataFrame(rows).to_excel(filename, index=False)
    print(f"Saved to {filename}")


def build_lin_line(board_number, dealer, vul_code, north, south, east, west) -> str:
    """Build a LIN line for a board."""
    return f"qx|o{board_number}|md|{dealer}{south},{west},{north},{east}|rh||ah|Board {board_number}|sv|{vul_code}|pg||"


# ----------------------------
# MAIN SCRAPE LOGIC
# ----------------------------
def scrape_boards():
    main_soup = fetch_soup(MAIN_URL)
    unique_links = get_unique_board_links(main_soup)

    score_union: List[Score] = []
    lin_lines: List[str] = []
    board_number_counter = 1

    for link, _ in unique_links:
        soup = fetch_soup(link)

        # Board info
        board_info_td = soup.find("td", class_="BrdDispl", colspan="3")
        if not board_info_td:
            continue
        board_number, dealer, vul_code = extract_dealer_vul(board_info_td.get_text(strip=True))

        # Extract hands
        hand_tds = [td for td in soup.find_all("td", class_="BrdDispl") if td != board_info_td]
        if len(hand_tds) < 4:
            continue
        north = clean_cards(hand_tds[0])
        west = clean_cards(hand_tds[1])
        east = clean_cards(hand_tds[2])
        south = clean_cards(hand_tds[3])

        # Extract scores
        scores = extract_scores(soup)
        for s in scores:
            s.BoardNumber = board_number_counter
            score_union.append(s)

        # Build LIN line
        lin_lines.append(build_lin_line(board_number, dealer, vul_code, north, south, east, west))
        board_number_counter += 1

    # Save outputs
    with open("boards.lin", "w") as f:
        for line in lin_lines:
            f.write(line + "\n")
    scores_to_excel(score_union)
    print(f"Saved {len(lin_lines)} boards to 'boards.lin'")


# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    scrape_boards()
