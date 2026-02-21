from nba_api.stats.endpoints import leaguedashplayerstats
import time
import random

def get_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    ]
    return {
        'Host': 'stats.nba.com',
        'User-Agent': random.choice(user_agents),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Origin': 'https://www.nba.com',
        'Referer': 'https://stats.nba.com/'
    }

print("Testing LeagueDashPlayerStats with high timeout...")
try:
    player_stats = leaguedashplayerstats.LeagueDashPlayerStats(
        season='2025-26',
        measure_type_detailed_defense='Base',
        per_mode_detailed='PerGame',
        headers=get_headers(),
        timeout=120
    ).get_data_frames()[0]
    print(f"Success! Got {len(player_stats)} player stats.")
except Exception as e:
    print(f"Failed: {e}")
