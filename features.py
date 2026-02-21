import os
import glob
import math
import numpy as np
import pandas as pd

DATA_DIR = "data"
PROCESSED_DATA_DIR = "processed_data"

if not os.path.exists(PROCESSED_DATA_DIR):
    os.makedirs(PROCESSED_DATA_DIR)

# Hardcoded NBA Arenas (Team Abbreviation -> {lat, lon, elevation_ft})
ARENAS = {
    'ATL': {'lat': 33.7573, 'lon': -84.3963, 'elev': 997, 'tz': -5},
    'BOS': {'lat': 42.3662, 'lon': -71.0621, 'elev': 13, 'tz': -5},
    'BKN': {'lat': 40.6826, 'lon': -73.9754, 'elev': 49, 'tz': -5},
    'CHA': {'lat': 35.2251, 'lon': -80.8392, 'elev': 728, 'tz': -5},
    'CHI': {'lat': 41.8806, 'lon': -87.6742, 'elev': 594, 'tz': -6},
    'CLE': {'lat': 41.4965, 'lon': -81.6881, 'elev': 653, 'tz': -5},
    'DAL': {'lat': 32.7905, 'lon': -96.8103, 'elev': 453, 'tz': -6},
    'DEN': {'lat': 39.7486, 'lon': -105.0075, 'elev': 5280, 'tz': -7},
    'DET': {'lat': 42.3411, 'lon': -83.0550, 'elev': 600, 'tz': -5},
    'GSW': {'lat': 37.7680, 'lon': -122.3877, 'elev': 16, 'tz': -8},
    'HOU': {'lat': 29.7508, 'lon': -95.3621, 'elev': 43, 'tz': -6},
    'IND': {'lat': 39.7639, 'lon': -86.1555, 'elev': 715, 'tz': -5},
    'LAC': {'lat': 34.0430, 'lon': -118.2673, 'elev': 267, 'tz': -8}, # Crypto.com / Intuit
    'LAL': {'lat': 34.0430, 'lon': -118.2673, 'elev': 267, 'tz': -8},
    'MEM': {'lat': 35.1381, 'lon': -90.0506, 'elev': 256, 'tz': -6},
    'MIA': {'lat': 25.7814, 'lon': -80.1870, 'elev': 10, 'tz': -5},
    'MIL': {'lat': 43.0451, 'lon': -87.9172, 'elev': 594, 'tz': -6},
    'MIN': {'lat': 44.9795, 'lon': -93.2761, 'elev': 830, 'tz': -6},
    'NOP': {'lat': 29.9490, 'lon': -90.0821, 'elev': -3, 'tz': -6},
    'NYK': {'lat': 40.7505, 'lon': -73.9934, 'elev': 36, 'tz': -5},
    'OKC': {'lat': 35.4634, 'lon': -97.5151, 'elev': 1195, 'tz': -6},
    'ORL': {'lat': 28.5392, 'lon': -81.3839, 'elev': 98, 'tz': -5},
    'PHI': {'lat': 39.9012, 'lon': -75.1720, 'elev': 13, 'tz': -5},
    'PHX': {'lat': 33.4457, 'lon': -112.0712, 'elev': 1086, 'tz': -7},
    'POR': {'lat': 45.5316, 'lon': -122.6668, 'elev': 30, 'tz': -8},
    'SAC': {'lat': 38.5802, 'lon': -121.4997, 'elev': 26, 'tz': -8},
    'SAS': {'lat': 29.4270, 'lon': -98.4375, 'elev': 650, 'tz': -6},
    'TOR': {'lat': 43.6435, 'lon': -79.3791, 'elev': 249, 'tz': -5},
    'UTA': {'lat': 40.7683, 'lon': -111.9011, 'elev': 4226, 'tz': -7},
    'WAS': {'lat': 38.8982, 'lon': -77.0209, 'elev': 40, 'tz': -5},
}


def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on earth in miles."""
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def engineered_features_for_player(df):
    """
    Given a raw DataFrame of a player's game logs (e.g., from nba_api), 
    engineer the required features.
    """
    df = df.copy()
    # Sort chronologically
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values('GAME_DATE').reset_index(drop=True)
    
    # Target variables: PTS and FG3M (3PM)
    # 1. Rolling averages (shifted to avoid leakage)
    for target in ['PTS', 'FG3M']:
        # shift by 1 to make sure current game stats are not included in rolling average
        df[f'{target}_3g_avg'] = df[target].shift(1).rolling(window=3, min_periods=1).mean()
        df[f'{target}_5g_avg'] = df[target].shift(1).rolling(window=5, min_periods=1).mean()
        df[f'{target}_10g_avg'] = df[target].shift(1).rolling(window=10, min_periods=1).mean()
        
    # 2. Fatigue Indicators
    df['DAYS_REST'] = df['GAME_DATE'].diff().dt.days
    df['B2B_FLAG'] = (df['DAYS_REST'] == 1).astype(int) # 1 day difference means back-to-back
    
    # Trailing 7-day games played (including current game, up to yesterday would be 6 days)
    # We want trailing games in previous 7 days
    # Since rolling on datetimes is tricky with irregular intervals, we can use a custom approach:
    # Set index to datetime to use '7D' rolling sum
    
    temp_df = df[['GAME_DATE']].copy()
    temp_df['count'] = 1
    temp_df = temp_df.set_index('GAME_DATE')
    # Rolling 7 days, shift by 1 day (so it only counts games in the last 7 days excluding today)
    temp_df = temp_df.rolling('7D').sum()
    df['GAMES_LAST_7D'] = temp_df['count'].values - 1 # subtract current game
    
    # 3. Geospatial & Travel Burden
    # Determine the home team of the current game to get lat/lon
    # MATCHUP format: 'LAL vs. BOS' (home) or 'LAL @ BOS' (away)
    def get_arena_team(row):
        matchup = row['MATCHUP']
        # The team playing at home is the one after '@', or if it's 'vs.' it's the team before 'vs.'
        if '@' in matchup:
            parts = matchup.split(' @ ')
            return parts[1]
        else:
            parts = matchup.split(' vs. ')
            return parts[0]
            
    df['HOME_TEAM'] = df.apply(get_arena_team, axis=1)
    
    # Map coordinates
    df['LAT'] = df['HOME_TEAM'].map(lambda x: ARENAS.get(x, {}).get('lat', np.nan))
    df['LON'] = df['HOME_TEAM'].map(lambda x: ARENAS.get(x, {}).get('lon', np.nan))
    df['ALTITUDE'] = df['HOME_TEAM'].map(lambda x: ARENAS.get(x, {}).get('elev', np.nan))
    df['TZ'] = df['HOME_TEAM'].map(lambda x: ARENAS.get(x, {}).get('tz', np.nan))
    
    # High altitude flag
    df['HIGH_ALTITUDE_FLAG'] = df['HOME_TEAM'].isin(['DEN', 'UTA']).astype(int)
    
    # Calculate Travel Distance and Direction
    df['PREV_LAT'] = df['LAT'].shift(1)
    df['PREV_LON'] = df['LON'].shift(1)
    df['PREV_TZ'] = df['TZ'].shift(1)
    
    def calc_dist(row):
        if pd.isna(row['PREV_LAT']) or pd.isna(row['LAT']):
            return 0.0
        return haversine(row['PREV_LAT'], row['PREV_LON'], row['LAT'], row['LON'])
        
    df['TRAVEL_DIST'] = df.apply(calc_dist, axis=1)
    
    # Eastward vs Westward travel
    # Lon difference: positive means went East, negative means went West
    def calc_direction(row):
        if pd.isna(row['PREV_LON']) or pd.isna(row['LON']):
            return 'None'
        diff = row['LON'] - row['PREV_LON']
        if diff > 0.5:
            return 'Eastward'
        elif diff < -0.5:
            return 'Westward'
        return 'None'
        
    df['TRAVEL_DIR'] = df.apply(calc_direction, axis=1)
    
    # Time zone shift bucketing {0, 1, 2, 3+}
    def calc_tz_shift(row):
        if pd.isna(row['PREV_TZ']) or pd.isna(row['TZ']):
            return '0'
        shift = abs(row['TZ'] - row['PREV_TZ'])
        if shift >= 3:
            return '3+'
        return str(int(shift))
        
    df['TZ_SHIFT'] = df.apply(calc_tz_shift, axis=1)
    
    return df


def process_all_files():
    print("Starting feature engineering phase...")
    parquet_files = glob.glob(os.path.join(DATA_DIR, "*.parquet"))
    
    all_processed = []
    
    for idx, f in enumerate(parquet_files):
        try:
            df = pd.read_parquet(f)
            processed_df = engineered_features_for_player(df)
            
            # Save the processed individual file
            base_name = os.path.basename(f)
            save_path = os.path.join(PROCESSED_DATA_DIR, base_name)
            processed_df.to_parquet(save_path, index=False)
            
            all_processed.append(processed_df)
            
        except Exception as e:
            print(f"Error processing {f}: {e}")
            
    if all_processed:
        master_df = pd.concat(all_processed, ignore_index=True)
        # Save master dataframe
        master_df.to_parquet(os.path.join(PROCESSED_DATA_DIR, "master_dataset.parquet"), index=False)
        print(f"Feature engineering complete. Prepared {len(master_df)} records.")
    else:
        print("No files were processed.")

if __name__ == "__main__":
    process_all_files()
