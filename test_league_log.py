from nba_api.stats.endpoints import leaguegamelog
import pandas as pd

custom_headers = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0',
    'Referer': 'https://stats.nba.com/',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

try:
    log = leaguegamelog.LeagueGameLog(season='2025-26', player_or_team_abbreviation='P', headers=custom_headers, timeout=60)
    df = log.get_data_frames()[0]
    print(f"Success! Retrieved {len(df)} rows for 2025-26.")
    print(df.head())
    print("Columns:", df.columns)
except Exception as e:
    print(f"Error: {e}")
