"""
Build data/wc2022.csv — WC2022 Qatar results + reconstructed pre-match closing odds.
Same format as wc2018.csv. Used only as the test_set (never for optimization).
"""
import csv
import json
import urllib.request
from pathlib import Path

ODDS: dict[tuple[str, str], tuple[float, float, float]] = {
    # Group A
    ("Qatar",        "Ecuador"):       (3.60, 3.20, 2.00),
    ("Senegal",      "Netherlands"):   (7.00, 4.33, 1.50),
    ("Qatar",        "Senegal"):       (5.50, 3.80, 1.62),
    ("Netherlands",  "Ecuador"):       (1.53, 4.20, 6.50),
    ("Ecuador",      "Senegal"):       (2.50, 3.10, 2.88),
    ("Netherlands",  "Qatar"):         (1.18, 7.00, 16.0),
    # Group B
    ("England",      "Iran"):          (1.40, 4.75, 9.00),
    ("USA",          "Wales"):         (2.38, 3.10, 3.10),
    ("Wales",        "Iran"):          (1.80, 3.50, 5.00),
    ("England",      "USA"):           (1.75, 3.60, 5.00),
    ("Wales",        "England"):       (7.50, 4.33, 1.50),
    ("Iran",         "USA"):           (3.00, 3.00, 2.50),
    # Group C
    ("Argentina",    "Saudi Arabia"):  (1.14, 7.50, 21.0),
    ("Mexico",       "Poland"):        (2.50, 3.10, 3.00),
    ("Poland",       "Saudi Arabia"):  (1.80, 3.50, 5.00),
    ("Argentina",    "Mexico"):        (1.44, 4.75, 8.00),
    ("Poland",       "Argentina"):     (7.50, 4.33, 1.50),
    ("Saudi Arabia", "Mexico"):        (4.00, 3.25, 1.95),
    # Group D
    ("Denmark",      "Tunisia"):       (1.72, 3.75, 5.50),
    ("France",       "Australia"):     (1.27, 6.00, 12.0),
    ("Tunisia",      "Australia"):     (2.88, 3.10, 2.63),
    ("France",       "Denmark"):       (1.72, 3.75, 5.50),
    ("Australia",    "Denmark"):       (5.50, 3.75, 1.72),
    ("Tunisia",      "France"):        (9.00, 5.00, 1.40),
    # Group E
    ("Germany",      "Japan"):         (1.22, 6.50, 15.0),
    ("Spain",        "Costa Rica"):    (1.14, 8.00, 22.0),
    ("Japan",        "Costa Rica"):    (1.72, 3.75, 5.50),
    ("Spain",        "Germany"):       (2.10, 3.20, 3.60),
    ("Japan",        "Spain"):         (8.50, 4.75, 1.44),
    ("Costa Rica",   "Germany"):       (15.0, 6.50, 1.22),
    # Group F
    ("Belgium",      "Canada"):        (1.44, 4.75, 8.00),
    ("Morocco",      "Croatia"):       (3.20, 3.10, 2.25),
    ("Belgium",      "Morocco"):       (1.50, 4.33, 7.50),
    ("Croatia",      "Canada"):        (1.57, 4.00, 6.50),
    ("Croatia",      "Belgium"):       (3.00, 3.20, 2.50),
    ("Canada",       "Morocco"):       (3.10, 3.20, 2.30),
    # Group G
    ("Switzerland",  "Cameroon"):      (1.50, 4.33, 7.50),
    ("Brazil",       "Serbia"):        (1.25, 6.00, 13.0),
    ("Cameroon",     "Serbia"):        (3.50, 3.20, 2.10),
    ("Brazil",       "Switzerland"):   (1.44, 4.75, 8.00),
    ("Cameroon",     "Brazil"):        (11.0, 6.00, 1.27),
    ("Serbia",       "Switzerland"):   (2.88, 3.10, 2.63),
    # Group H
    ("Uruguay",      "South Korea"):   (1.83, 3.50, 5.00),
    ("Portugal",     "Ghana"):         (1.40, 4.75, 9.00),
    ("South Korea",  "Ghana"):         (2.88, 3.10, 2.50),
    ("Portugal",     "Uruguay"):       (1.80, 3.60, 4.75),
    ("Ghana",        "Uruguay"):       (5.00, 3.60, 1.80),
    ("South Korea",  "Portugal"):      (8.00, 4.75, 1.50),
    # Round of 16
    ("Netherlands",  "USA"):           (1.62, 3.80, 6.00),
    ("Argentina",    "Australia"):     (1.30, 5.50, 11.0),
    ("France",       "Poland"):        (1.33, 5.00, 10.0),
    ("England",      "Senegal"):       (1.57, 4.00, 6.50),
    ("Japan",        "Croatia"):       (3.40, 3.20, 2.10),
    ("Brazil",       "South Korea"):   (1.18, 7.00, 17.0),
    ("Morocco",      "Spain"):         (9.00, 4.75, 1.40),
    ("Portugal",     "Switzerland"):   (1.75, 3.60, 5.25),
    # Quarter-finals
    ("Croatia",      "Brazil"):        (5.50, 3.75, 1.72),
    ("Netherlands",  "Argentina"):     (2.88, 3.10, 2.50),
    ("Morocco",      "Portugal"):      (8.00, 4.75, 1.50),
    ("England",      "France"):        (2.88, 3.20, 2.38),
    # Semi-finals
    ("Argentina",    "Croatia"):       (2.10, 3.25, 3.60),
    ("France",       "Morocco"):       (1.33, 5.00, 10.0),
    # Third place
    ("Croatia",      "Morocco"):       (2.50, 3.10, 3.00),
    # Final
    ("Argentina",    "France"):        (2.25, 3.25, 3.25),
}

URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2022/worldcup.json"


def fetch_results() -> list[dict]:
    with urllib.request.urlopen(URL) as r:
        data = json.loads(r.read())
    rows = []
    for m in data["matches"]:
        score = m.get("score")
        if not score:
            continue
        ft = score.get("ft") or score.get("et") or score.get("p")
        if not ft:
            continue
        if isinstance(ft, list):
            hg, ag = int(ft[0]), int(ft[1])
        else:
            hg, ag = map(int, str(ft).split())
        rows.append({"home": m["team1"], "away": m["team2"], "hg": hg, "ag": ag})
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
    build_csv(Path("data/wc2022.csv"))
