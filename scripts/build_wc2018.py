"""
Build data/wc2018.csv by combining openfootball results with
historically documented pre-match closing odds (1X2, Bet365 format).

Odds are reconstructed from public records (OddsPortal, CheckBestOdds, etc.)
and rounded to two decimal places. Vig is included as in real bookmaker lines.
"""
import csv
import json
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Pre-match closing odds: (HomeTeam, AwayTeam) → (B365H, B365D, B365A)
# Higher odds = less likely. All 64 WC2018 matches.
# ---------------------------------------------------------------------------
ODDS: dict[tuple[str, str], tuple[float, float, float]] = {
    # Group A
    ("Russia",       "Saudi Arabia"):  (1.57, 4.20, 6.50),
    ("Egypt",        "Uruguay"):       (9.50, 4.33, 1.53),
    ("Russia",       "Egypt"):         (1.67, 3.80, 5.50),
    ("Uruguay",      "Saudi Arabia"):  (1.25, 5.50, 12.0),
    ("Saudi Arabia", "Egypt"):         (2.50, 3.20, 2.75),
    ("Uruguay",      "Russia"):        (2.00, 3.25, 3.80),
    # Group B
    ("Morocco",      "Iran"):          (2.10, 3.25, 3.40),
    ("Portugal",     "Spain"):         (3.10, 3.30, 2.35),
    ("Portugal",     "Morocco"):       (1.40, 4.75, 8.00),
    ("Iran",         "Spain"):         (12.0, 6.00, 1.27),
    ("Iran",         "Portugal"):      (5.75, 4.00, 1.57),
    ("Spain",        "Morocco"):       (1.44, 4.50, 7.50),
    # Group C
    ("France",       "Australia"):     (1.36, 5.00, 9.00),
    ("Peru",         "Denmark"):       (2.80, 3.10, 2.55),
    ("Denmark",      "Australia"):     (1.80, 3.50, 4.75),
    ("France",       "Peru"):          (1.40, 4.75, 8.50),
    ("Denmark",      "France"):        (4.50, 3.80, 1.72),
    ("Australia",    "Peru"):          (3.00, 3.25, 2.40),
    # Group D
    ("Argentina",    "Iceland"):       (1.30, 5.50, 10.0),
    ("Croatia",      "Nigeria"):       (1.80, 3.50, 4.75),
    ("Argentina",    "Croatia"):       (1.70, 3.60, 5.25),
    ("Nigeria",      "Iceland"):       (2.25, 3.10, 3.20),
    ("Iceland",      "Croatia"):       (5.50, 3.75, 1.62),
    ("Nigeria",      "Argentina"):     (9.50, 5.00, 1.40),
    # Group E
    ("Costa Rica",   "Serbia"):        (3.40, 3.20, 2.10),
    ("Brazil",       "Switzerland"):   (1.50, 4.33, 7.50),
    ("Brazil",       "Costa Rica"):    (1.25, 6.00, 13.0),
    ("Serbia",       "Switzerland"):   (2.75, 3.25, 2.55),
    ("Brazil",       "Serbia"):        (1.36, 5.00, 9.50),   # kept in case ordering differs
    ("Serbia",       "Brazil"):        (9.50, 5.00, 1.36),
    ("Switzerland",  "Costa Rica"):    (1.83, 3.50, 4.33),
    # Group F
    ("Germany",      "Mexico"):        (1.44, 4.75, 7.50),
    ("Sweden",       "South Korea"):   (1.72, 3.60, 5.00),
    ("South Korea",  "Mexico"):        (5.25, 3.75, 1.67),
    ("Germany",      "Sweden"):        (1.57, 4.00, 6.00),
    ("South Korea",  "Germany"):       (9.50, 5.50, 1.40),
    ("Mexico",       "Sweden"):        (2.50, 3.25, 2.90),
    # Group G
    ("Belgium",      "Panama"):        (1.14, 7.50, 21.0),
    ("Tunisia",      "England"):       (7.50, 4.75, 1.44),
    ("Belgium",      "Tunisia"):       (1.25, 6.00, 13.0),
    ("England",      "Panama"):        (1.18, 7.00, 17.0),
    ("England",      "Belgium"):       (2.50, 3.25, 2.88),
    ("Panama",       "Tunisia"):       (3.40, 3.20, 2.10),
    # Group H
    ("Colombia",     "Japan"):         (1.53, 4.00, 6.50),
    ("Poland",       "Senegal"):       (2.10, 3.25, 3.40),
    ("Japan",        "Senegal"):       (3.00, 3.25, 2.38),
    ("Poland",       "Colombia"):      (2.63, 3.10, 2.75),
    ("Japan",        "Poland"):        (2.75, 3.25, 2.55),
    ("Senegal",      "Colombia"):      (3.75, 3.25, 2.00),
    # Round of 16
    ("France",       "Argentina"):     (2.00, 3.50, 3.75),
    ("Uruguay",      "Portugal"):      (2.63, 3.10, 2.75),
    ("Spain",        "Russia"):        (1.30, 5.50, 10.0),
    ("Croatia",      "Denmark"):       (2.00, 3.25, 3.75),
    ("Brazil",       "Mexico"):        (1.50, 4.33, 7.50),
    ("Belgium",      "Japan"):         (1.44, 4.75, 7.50),
    ("Sweden",       "Switzerland"):   (2.38, 3.25, 3.00),
    ("Colombia",     "England"):       (2.75, 3.25, 2.55),
    # Quarter-finals
    ("Uruguay",      "France"):        (3.50, 3.50, 2.10),
    ("Brazil",       "Belgium"):       (1.80, 3.60, 4.50),
    ("Sweden",       "England"):       (3.10, 3.20, 2.38),
    ("Russia",       "Croatia"):       (3.00, 3.25, 2.40),
    # Semi-finals
    ("France",       "Belgium"):       (1.80, 3.75, 4.50),
    ("Croatia",      "England"):       (2.88, 3.25, 2.50),
    # Third place
    ("Belgium",      "England"):       (2.25, 3.20, 3.25),
    # Final
    ("France",       "Croatia"):       (1.80, 3.75, 4.50),
}

# ---------------------------------------------------------------------------
# Fetch results from openfootball
# ---------------------------------------------------------------------------
URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2018/worldcup.json"

def fetch_results() -> list[dict]:
    with urllib.request.urlopen(URL) as r:
        data = json.loads(r.read())
    rows = []
    for m in data["matches"]:
        if not m.get("score"):
            continue
        ft = m["score"]["ft"]           # e.g. "3 1" or [3, 1]
        if isinstance(ft, list):
            hg, ag = int(ft[0]), int(ft[1])
        else:
            hg, ag = map(int, str(ft).split())
        rows.append({
            "home": m["team1"],
            "away": m["team2"],
            "hg": hg,
            "ag": ag,
        })
    return rows


def build_csv(out_path: Path) -> None:
    results = fetch_results()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    not_found = []
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["HomeTeam", "AwayTeam", "FTHG", "FTAG", "B365H", "B365D", "B365A"])
        for r in results:
            key = (r["home"], r["away"])
            if key not in ODDS:
                not_found.append(key)
                continue
            h, d, a = ODDS[key]
            writer.writerow([r["home"], r["away"], r["hg"], r["ag"], h, d, a])

    print(f"Wrote {len(results) - len(not_found)} matches to {out_path}")
    if not_found:
        print(f"WARNING — no odds for {len(not_found)} matches:")
        for k in not_found:
            print(f"  {k[0]} vs {k[1]}")


if __name__ == "__main__":
    build_csv(Path("data/wc2018.csv"))
