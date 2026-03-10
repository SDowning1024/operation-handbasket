import requests
import json
import time
from datetime import datetime, timezone
from supabase import create_client

def implied_probability(odds):
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)

def expected_value(win_prob, odds):
    if odds > 0:
        profit = odds / 100
    else:
        profit = 100 / abs(odds)
    return (win_prob * profit) - ((1 - win_prob) * 1)

def is_better_odds(new_odds, current_odds):
    if current_odds is None:
        return True

    # Positive odds: bigger is better (+140 > +120)
    if new_odds > 0 and current_odds > 0:
        return new_odds > current_odds

    # Negative odds: closer to zero is better (-110 > -140)
    if new_odds < 0 and current_odds < 0:
        return new_odds > current_odds

    # Positive odds are better than negative odds
    if new_odds > 0 and current_odds < 0:
        return True

    return False

def parse_commence_time(commence_time_str):
    if not commence_time_str:
        return None
    try:
        return datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))
    except Exception:
        return None

def is_live_game(commence_dt):
    if commence_dt is None:
        return False

    now = datetime.now(timezone.utc)
    seconds_since_start = (now - commence_dt).total_seconds()

    # Treat as live if game started and is within a broad live window
    # This is a practical approximation.
    return 0 <= seconds_since_start <= 5 * 60 * 60

API_KEY = "923084e5f569df661c0ffbed6df3bd23"
SUPABASE_URL = "https://fesljajdsbxodzrlqnno.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZlc2xqYWpkc2J4b2R6cmxxbm5vIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMwMTkxNjgsImV4cCI6MjA4ODU5NTE2OH0.iR8ilbhRwhPTVi0fo6KgGlFPVrupS8b-1RHE6nf01c0"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

REFRESH_SECONDS = 30
ALERT_EV_THRESHOLD = 0.03
LIVE_ALERT_EV_THRESHOLD = 0.04

BOOK_WEIGHTS = {
    "pinnacle": 3.0,
    "circa": 3.0,
    "betonlineag": 2.0,
    "bovada": 1.5,
    "draftkings": 1.0,
    "fanduel": 1.0,
    "betrivers": 1.0,
    "betmgm": 1.0,
    "caesars": 1.0,
    "bet365": 1.0,
    "lowvig": 1.0
}

SPORTS = [
    "basketball_nba",
    "basketball_ncaab",
    "americanfootball_nfl",
    "americanfootball_ncaaf",
    "baseball_mlb",
    "baseball_ncaa",
    "icehockey_nhl",
    "icehockey_ncaah",
    "tennis_atp",
    "tennis_wta",
    "tennis_atp_challenger",
    "softball_ncaa"
]

print("SPORTS DETECTED:")
for sport in SPORTS:
    print("-", sport)

while True:
    print("=" * 70)
    print("CHECKED AT:", time.strftime("%Y-%m-%d %H:%M:%S"))

    try:
        for SPORT in SPORTS:
            url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"

            params = {
                "apiKey": API_KEY,
                "regions": "us",
                "markets": "h2h",
                "oddsFormat": "american",
            }

            response = requests.get(url, params=params)
            print("STATUS:", response.status_code, "| SPORT:", SPORT)

            data = response.json()

            if not isinstance(data, list):
                print(f"Skipping {SPORT} - unsupported or invalid response")
                print(json.dumps(data, indent=2)[:300])
                continue

            print(f"{SPORT}: {len(data)} games returned")

            for game in data:
                home = game.get("home_team")
                away = game.get("away_team")
                commence_time = game.get("commence_time")
                commence_dt = parse_commence_time(commence_time)
                live_flag = is_live_game(commence_dt)

                bookmakers = game.get("bookmakers", [])

                game_status = "LIVE" if live_flag else "PREGAME"
                print(f"\n[{game_status}] {SPORT} | {away} at {home}")

                offers = []

                for book in bookmakers:
                    book_name = book.get("key")

                    for market in book.get("markets", []):
                        if market.get("key") != "h2h":
                            continue

                        for outcome in market.get("outcomes", []):
                            team = outcome.get("name")
                            odds = outcome.get("price")

                            if odds is None:
                                continue

                            prob = implied_probability(odds)

                            offers.append({
                                "team": team,
                                "sportsbook": book_name,
                                "odds": odds,
                                "implied_probability": prob
                            })

                if not offers:
                    continue

                # Find best line for each team
                best_offers = {}

                for offer in offers:
                    team = offer["team"]
                    odds = offer["odds"]

                    if team not in best_offers:
                        best_offers[team] = offer
                    else:
                        current_best = best_offers[team]
                        if is_better_odds(odds, current_best["odds"]):
                            best_offers[team] = offer

                # Evaluate only best line for each team
                for team, best_offer in best_offers.items():
                    book_name = best_offer["sportsbook"]
                    odds = best_offer["odds"]
                    prob = best_offer["implied_probability"]

                    other_offers = [
                        o for o in offers
                        if o["team"] == team and o["sportsbook"] != book_name
                    ]

                    if not other_offers:
                        continue

                    weighted_sum = 0
                    weight_total = 0

                    for o in other_offers:
                        weight = BOOK_WEIGHTS.get(o["sportsbook"], 1.0)
                        weighted_sum += o["implied_probability"] * weight
                        weight_total += weight

                    if weight_total == 0:
                        continue

                    fair_prob = weighted_sum / weight_total
                    ev = expected_value(fair_prob, odds)
                    edge = fair_prob - prob

                    print(
                        f"BEST LINE | {team} | {book_name} | Odds: {odds} | "
                        f"Book Prob: {prob:.3f} | Fair Prob: {fair_prob:.3f} | "
                        f"Edge: {edge:.3f} | EV: {ev:.3f}"
                    )

                    qualifies = ev > 0.01

                    if qualifies:
                        row = {
                            "sport": SPORT,
                            "home_team": home,
                            "away_team": away,
                            "team": team,
                            "sportsbook": book_name,
                            "american_odds": odds,
                            "win_probability": fair_prob,
                            "implied_probability": prob,
                            "expected_value": ev,
                            "edge_percent": edge,
                            "qualifies": True
                        }

                        existing = (
                            supabase.table("edge_candidates")
                            .select("id")
                            .eq("sport", SPORT)
                            .eq("home_team", home)
                            .eq("away_team", away)
                            .eq("team", team)
                            .eq("sportsbook", book_name)
                            .eq("american_odds", odds)
                            .limit(1)
                            .execute()
                        )

                        if existing.data:
                            print("Duplicate found, skipping insert")
                        else:
                            supabase.table("edge_candidates").insert(row).execute()
                            print("🔥 Saved +EV best line to Supabase")

                    # Alerts
                    if ev >= ALERT_EV_THRESHOLD:
                        print(
                            f"\n🚨 OPERATION HANDBASKET ALERT 🚨\n"
                            f"Type: {'LIVE' if live_flag else 'PREGAME'}\n"
                            f"Sport: {SPORT}\n"
                            f"Game: {away} at {home}\n"
                            f"Team: {team}\n"
                            f"Book: {book_name}\n"
                            f"Odds: {odds}\n"
                            f"Fair Prob: {fair_prob:.3f}\n"
                            f"Edge: {edge:.3f}\n"
                            f"EV: {ev:.3f}\n"
                        )

                    if live_flag and ev >= LIVE_ALERT_EV_THRESHOLD:
                        try:
                            print("\a")  # terminal beep on Windows/macOS terminals that support it
                        except Exception:
                            pass

    except Exception as e:
        print("ERROR:", e)

    print(f"Waiting {REFRESH_SECONDS} seconds...\n")
    time.sleep(REFRESH_SECONDS)