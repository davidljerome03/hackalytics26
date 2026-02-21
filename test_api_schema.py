import os
import pandas as pd
from nba_api.stats.endpoints import playergamelog, leaguegamelog
from predict import get_headers

try:
    print("Testing playergamelog...")
    # LeBron ID 2544
    plog = playergamelog.PlayerGameLog(player_id=2544, season='2025-26', headers=get_headers(), timeout=30).get_data_frames()[0]
    print(f"PlayerGameLog columns: {plog.columns.tolist()}")
    print(f"PlayerGameLog GAME_ID type/sample: {type(plog['Game_ID'].iloc[0]) if 'Game_ID' in plog.columns else type(plog['GAME_ID'].iloc[0])} {plog['Game_ID'].iloc[0] if 'Game_ID' in plog.columns else plog['GAME_ID'].iloc[0]}")
except Exception as e:
    print(f"PlayerGameLog failed: {e}")

try:
    print("\nTesting leaguegamelog...")
    llog = leaguegamelog.LeagueGameLog(season='2025-26', player_or_team_abbreviation='P', headers=get_headers(), timeout=30).get_data_frames()[0]
    print(f"LeagueGameLog columns: {llog.columns.tolist()}")
    print(f"LeagueGameLog GAME_ID type/sample: {type(llog['GAME_ID'].iloc[0])} {llog['GAME_ID'].iloc[0]}")
except Exception as e:
    print(f"LeagueGameLog failed: {e}")
