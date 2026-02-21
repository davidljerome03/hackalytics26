import os
import time
import pandas as pd
import requests
from requests.exceptions import ReadTimeout
from nba_api.stats.endpoints import leaguedashplayerstats, leaguegamelog
from nba_api.stats.static import players

DATA_DIR = "data"

# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

import random

# Generate rotating headers to avoid timeouts/blocks
def get_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0'
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

# The latest full season is 2025-26 as per requirements.
# We will pull this season and the past three seasons.
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']


def get_active_rotational_players():
    """
    Fetch active players from the static players list.
    Since leaguedashplayerstats is consistently timing out, we will use the local static data map.
    """
    print("Fetching active players using static player list to avoid timeouts...")
    
    nba_players = players.get_players()
    active_players = [p for p in nba_players if p['is_active']]
    
    # Returning all active players
    player_dict = {p['id']: p['full_name'] for p in active_players}
    print(f"Found {len(player_dict)} active players.")
    return player_dict


def download_bulk_game_logs(active_players_dict, seasons):
    """
    Download ALL game logs for the specified seasons in bulk.
    Filter for active players, then save out individual dataframes.
    """
    print(f"Downloading bulk game logs for {len(seasons)} seasons...")
    all_seasons_data = []

    for season in seasons:
        max_retries = 8
        for attempt in range(max_retries):
            try:
                print(f"  Fetching all player logs for {season}...")
                time.sleep(random.uniform(2.0, 4.0)) # Polite sleep
                
                log = leaguegamelog.LeagueGameLog(
                    season=season, 
                    player_or_team_abbreviation='P', 
                    headers=get_headers(), 
                    timeout=60
                )
                df = log.get_data_frames()[0]
                
                if not df.empty:
                    all_seasons_data.append(df)
                    print(f"  -> Successfully retrieved {len(df)} logs for {season}.")
                break # Success, exit retry loop
                    
            except ReadTimeout:
                print(f"API Read Timeout on season {season} (Attempt {attempt+1}). Retrying...")
                time.sleep(2 ** attempt + random.uniform(4.0, 8.0))
            except Exception as e:
                print(f"Error fetching season {season} (Attempt {attempt+1}): {e}")
                time.sleep(2 ** attempt + random.uniform(3.0, 6.0))
    
    if not all_seasons_data:
        print("Failed to fetch any bulk season data.")
        return
        
    # Combine all seasons into one massive dataframe
    master_df = pd.concat(all_seasons_data, ignore_index=True)
    
    # Filter for only the active rotational players we care about
    active_ids = list(active_players_dict.keys())
    filtered_df = master_df[master_df['PLAYER_ID'].isin(active_ids)]
    
    print(f"\nExtracted {len(filtered_df)} total games for our {len(active_ids)} active players.")
    
    # Group by player and save to individual parquet files
    # features.py expects file format: [Player_Name]_[Player_ID]_logs.parquet
    grouped = filtered_df.groupby('PLAYER_ID')
    
    for player_id, group_df in grouped:
        player_name = active_players_dict.get(player_id, "Unknown_Player")
        filename = f"{player_name.replace(' ', '_')}_{player_id}_logs.parquet"
        filepath = os.path.join(DATA_DIR, filename)
        
        # Save to parquet
        group_df.to_parquet(filepath, index=False)
        
    print(f"Saved {len(grouped)} individual player parquet files to {DATA_DIR}/")


def run_ingestion():
    print("Starting data ingestion phase...")
    # 1. Get rotational players from the target season
    active_players = get_active_rotational_players()
    
    if not active_players:
        print("Failed to get players. Exiting.")
        return
        
    # 2. Download game logs in bulk, then split by player
    download_bulk_game_logs(active_players, SEASONS)
    print("Data ingestion complete.")


if __name__ == "__main__":
    run_ingestion()
