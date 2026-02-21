import os
import time
import pandas as pd
import requests
from requests.exceptions import ReadTimeout
from nba_api.stats.endpoints import leaguedashplayerstats, playergamelog
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
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
    ]
    return {
        'Host': 'stats.nba.com',
        'User-Agent': random.choice(user_agents),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Origin': 'https://www.nba.com',
        'Referer': 'https://www.nba.com/',
    }

# The latest full season is 2025-26 as per requirements.
# We will pull this season and the past three seasons.
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']


def get_active_rotational_players(season='2025-26', min_mpg=12.0):
    """
    Fetch players who played in the given season and averaged >= min_mpg.
    """
    print(f"Fetching active rotational players (>= {min_mpg} MPG) for season {season}...")
    
    # Retry mechanism for leaguedashplayerstats
    max_retries = 8
    for attempt in range(max_retries):
        try:
            player_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season,
                measure_type_detailed_defense='Base',
                per_mode_detailed='PerGame',
                headers=get_headers(),
                timeout=30 # Lower timeout to fail fast and trigger retry
            ).get_data_frames()[0]
            
            # Filter by MPG and restrict to top 250 players
            rotational_players = player_stats[player_stats['MIN'] >= min_mpg]
            rotational_players = rotational_players.sort_values('MIN', ascending=False).head(250)
            
            player_ids = rotational_players['PLAYER_ID'].tolist()
            player_names = rotational_players['PLAYER_NAME'].tolist()
            
            print(f"Found {len(player_ids)} rotational players.")
            return dict(zip(player_ids, player_names))
            
        except ReadTimeout:
            print(f"Attempt {attempt + 1} Read Timeout. Retrying...")
            time.sleep(2 ** attempt + random.uniform(3.0, 6.0))
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt + random.uniform(2.0, 5.0)) # Exponential backoff
            
    print("Failed to fetch active players after multiple attempts.")
    print("Falling back to static active player list (top 200 players).")
    nba_players = players.get_players()
    active_players = [p for p in nba_players if p['is_active']]
    # Just take the first 200 to keep the fetch reasonable
    active_players = active_players[:200]
    return {p['id']: p['full_name'] for p in active_players}


def download_game_logs_for_seasons(player_dict, seasons):
    """
    Download game logs for the specified players across the specified seasons.
    Stores data in Parquet files per player.
    """
    total_players = len(player_dict)
    
    for i, (player_id, player_name) in enumerate(player_dict.items(), 1):
        filename = f"{player_name.replace(' ', '_')}_{player_id}_logs.parquet"
        filepath = os.path.join(DATA_DIR, filename)
        
        # Resumability: Skip if we already downloaded this player
        if os.path.exists(filepath):
            print(f"[{i}/{total_players}] Skipping {player_name} (already downloaded).")
            continue
            
        print(f"[{i}/{total_players}] Fetching data for {player_name}...")
        
        all_logs = []
        for season in seasons:
            max_retries = 8
            for attempt in range(max_retries):
                try:
                    # Random jitter between 2.0 and 4.0 seconds
                    time.sleep(random.uniform(2.0, 4.0))
                    logs = playergamelog.PlayerGameLog(
                        player_id=player_id,
                        season=season,
                        headers=get_headers(),
                        timeout=30 # Lower timeout to fail fast
                    ).get_data_frames()[0]
                    
                    if not logs.empty:
                        all_logs.append(logs)
                    break # Success, exit retry loop
                    
                except ReadTimeout:
                    print(f"API Read Timeout on season {season} for {player_name} (Attempt {attempt+1}). Retrying...")
                    time.sleep(2 ** attempt + random.uniform(4.0, 8.0))
                except Exception as e:
                    print(f"Error fetching season {season} for {player_name} (Attempt {attempt+1}): {e}")
                    time.sleep(2 ** attempt + random.uniform(3.0, 6.0)) # Exponential backoff + jitter
                
        if all_logs:
            player_df = pd.concat(all_logs, ignore_index=True)
            # Save to parquet
            player_df.to_parquet(filepath, index=False)
            print(f"  -> Saved {len(player_df)} games to {filepath}")
        else:
            print(f"  -> No data found for {player_name}.")
            
        # Extra delay between players to cool down
        time.sleep(random.uniform(3.0, 5.0))


def run_ingestion():
    print("Starting data ingestion phase...")
    # 1. Get rotational players from the target season
    active_players = get_active_rotational_players(season='2025-26', min_mpg=12.0)
    
    if not active_players:
        print("Failed to get players. Exiting.")
        return
        
    # 2. Download game logs for these players across last 4 seasons
    download_game_logs_for_seasons(active_players, SEASONS)
    print("Data ingestion complete.")


if __name__ == "__main__":
    run_ingestion()
