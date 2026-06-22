"""
Download top-5 European league data from football-data.co.uk with O/U odds.

Leagues: Premier League (E0), Bundesliga (D1), La Liga (SP1),
         Serie A (I1), Ligue 1 (F1)
Seasons: 2010-11 through 2023-24 (14 seasons, ~18k matches)

Includes B365>2.5 / B365<2.5 real over/under odds alongside 1x2.
Writes to data/leagues_v2.csv.
"""
import csv
import io
import urllib.request

LEAGUES = ["E0", "D1", "SP1", "I1", "F1"]

# 14 seasons: 2010-11 through 2023-24
SEASONS = [
    "1011", "1112", "1213", "1314", "1415",
    "1516", "1617", "1718", "1819", "1920",
    "2021", "2122", "2223", "2324",
]

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"

REQUIRED_1X2 = {"HomeTeam", "AwayTeam", "FTHG", "FTAG", "B365H", "B365D", "B365A"}
OU_COLS = ["B365>2.5", "B365<2.5"]
OUT_COLS = ["HomeTeam", "AwayTeam", "FTHG", "FTAG", "B365H", "B365D", "B365A", "B365O25", "B365U25"]


def fetch(url: str) -> list[dict]:
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            raw = r.read().decode("utf-8", errors="replace")
        rows = list(csv.DictReader(io.StringIO(raw)))
        out = []
        for row in rows:
            if not REQUIRED_1X2.issubset(row.keys()):
                continue
            if not all(row.get(c, "").strip() for c in REQUIRED_1X2):
                continue
            try:
                float(row["B365H"]); float(row["B365D"]); float(row["B365A"])
                int(row["FTHG"]); int(row["FTAG"])
            except (ValueError, TypeError):
                continue

            # O/U odds — use if available, else None
            try:
                ou_over  = str(float(row["B365>2.5"])) if row.get("B365>2.5", "").strip() else ""
                ou_under = str(float(row["B365<2.5"])) if row.get("B365<2.5", "").strip() else ""
            except (ValueError, TypeError):
                ou_over = ou_under = ""

            out.append({
                "HomeTeam": row["HomeTeam"],
                "AwayTeam": row["AwayTeam"],
                "FTHG":     row["FTHG"],
                "FTAG":     row["FTAG"],
                "B365H":    row["B365H"],
                "B365D":    row["B365D"],
                "B365A":    row["B365A"],
                "B365O25":  ou_over,
                "B365U25":  ou_under,
            })
        return out
    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def main():
    all_rows = []
    has_ou = 0
    for season in SEASONS:
        for league in LEAGUES:
            url = BASE_URL.format(season=season, league=league)
            rows = fetch(url)
            season_ou = sum(1 for r in rows if r["B365O25"])
            has_ou += season_ou
            print(f"  {season} {league}: {len(rows)} matches  ({season_ou} with O/U)")
            all_rows.extend(rows)

    total = len(all_rows)
    print(f"\nTotal: {total} matches  ({has_ou} with B365 O/U odds, {has_ou*100//total}%)")

    with open("data/leagues_v2.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(all_rows)
    print("Written to data/leagues_v2.csv")


if __name__ == "__main__":
    main()
