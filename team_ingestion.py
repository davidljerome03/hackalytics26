import os
import time
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats
from ingestion import get_headers

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# We want the same 4 seasons we used for player logs
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
TEAM_CACHE_FILE = os.path.join(DATA_DIR, "team_defensive_metrics.parquet")

def fetch_advanced_team_stats(seasons):
    """
    Independent script to fetch advanced team metrics (Pace, DefRtg, etc) per season.
    Does not interfere with the player ingestion pipeline.
    """
    print(f"Fetching Advanced Team Metrics for {len(seasons)} seasons...")
    all_seasons_data = []
    
    for season in seasons:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"  Pulling advanced stats for {season}...")
                time.sleep(2) # Polite sleep
                
                log = leaguedashteamstats.LeagueDashTeamStats(
                    season=season,
                    measure_type_detailed_defense='Advanced',
                    per_mode_detailed='PerGame',
                    headers=get_headers(),
                    timeout=30
                )
                
                df = log.get_data_frames()[0]
                
                if not df.empty:
                    df['SEASON'] = season
                    if attempt == 0 and season == seasons[0]:
                        print("Returned columns:", df.columns.tolist())
                    all_seasons_data.append(df)
                    print(f"  -> Success: {len(df)} teams retrieved.")
                break
                
            except Exception as e:
                print(f"  Error on {season} (Attempt {attempt+1}): {e}")
                time.sleep(5)
                
    if not all_seasons_data:
        print("Failed to pull any team metrics.")
        return None
        
    master_team_df = pd.concat(all_seasons_data, ignore_index=True)
    return master_team_df

if __name__ == "__main__":
    df = fetch_advanced_team_stats(SEASONS)
    if df is not None:
        df.to_parquet(TEAM_CACHE_FILE, index=False)
        print(f"\nSaved {len(df)} total team-season records to {TEAM_CACHE_FILE}")
