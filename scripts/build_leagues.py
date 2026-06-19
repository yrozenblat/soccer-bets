"""
Download top-5 European league data from football-data.co.uk and build
a combined training CSV in the same format as wc2018.csv.

Leagues: Premier League (E0), Bundesliga (D1), La Liga (SP1),
         Serie A (I1), Ligue 1 (F1)
Seasons: 2018-19 through 2023-24 (6 seasons, pre-WC2026)

Each file is fetched, filtered to rows with complete B365 odds, and written
to data/leagues.csv.
"""
import csv
import io
import urllib.request

LEAGUES = ["E0", "D1", "SP1", "I1", "F1"]
SEASONS = ["1819", "1920", "2021", "2122", "2223", "2324"]

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"

REQUIRED_COLS = {"HomeTeam", "AwayTeam", "FTHG", "FTAG", "B365H", "B365D", "B365A"}
OUT_COLS = ["HomeTeam", "AwayTeam", "FTHG", "FTAG", "B365H", "B365D", "B365A"]


def fetch(url: str) -> list[dict]:
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            raw = r.read().decode("utf-8", errors="replace")
        rows = list(csv.DictReader(io.StringIO(raw)))
        # Keep only rows with all required columns present and non-empty
        out = []
        for row in rows:
            if not REQUIRED_COLS.issubset(row.keys()):
                continue
            if not all(row.get(c, "").strip() for c in REQUIRED_COLS):
                continue
            try:
                float(row["B365H"]); float(row["B365D"]); float(row["B365A"])
                int(row["FTHG"]); int(row["FTAG"])
            except (ValueError, TypeError):
                continue
            out.append({c: row[c] for c in OUT_COLS})
        return out
    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def main():
    all_rows = []
    for season in SEASONS:
        for league in LEAGUES:
            url = BASE_URL.format(season=season, league=league)
            rows = fetch(url)
            print(f"  {season} {league}: {len(rows)} matches")
            all_rows.extend(rows)

    print(f"\nTotal: {len(all_rows)} matches across {len(SEASONS)} seasons x {len(LEAGUES)} leagues")

    out_path = "data/leagues.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(all_rows)
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
