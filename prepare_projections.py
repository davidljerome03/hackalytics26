import os
import time
import pandas as pd
import numpy as np
import joblib
from predict import fetch_live_player_logs
from features import engineered_features_for_player
from nba_api.stats.static import players

DATA_DIR = "data"
PROCESSED_DATA_DIR = "processed_data"
SCHEDULE_FILE = os.path.join(DATA_DIR, "upcoming_games.csv")
MASTER_FILE = os.path.join(PROCESSED_DATA_DIR, "master_dataset.parquet")
MODEL_FILES = {
    'PTS': os.path.join(PROCESSED_DATA_DIR, "xgb_pts_model.joblib"),
    'AST': os.path.join(PROCESSED_DATA_DIR, "xgb_ast_model.joblib"),
    'REB': os.path.join(PROCESSED_DATA_DIR, "xgb_reb_model.joblib"),
    'PRA': os.path.join(PROCESSED_DATA_DIR, "xgb_pra_model.joblib"),
}

PROJECTIONS_FILE = os.path.join(DATA_DIR, "upcoming_projections.csv")

def get_active_rotational_players():
    # Load same cached players as ingestion
    nba_players = players.get_players()
    active_players = [p for p in nba_players if p['is_active']]
    return {p['id']: p['full_name'] for p in active_players}

def prepare_and_run_projections():
    print("Loading schedule and models...")
    if not os.path.exists(SCHEDULE_FILE):
        print(f"File {SCHEDULE_FILE} missing! Run fetch_schedule.py first.")
        return
        
    for name, mfile in MODEL_FILES.items():
        if not os.path.exists(mfile):
            print(f"Model {name} missing at {mfile}! Run model.py first.")
            return
            
    if not os.path.exists(MASTER_FILE):
        print("Master data missing! Run features.py first.")
        return
        
    schedule_df = pd.read_csv(SCHEDULE_FILE)
    schedule_df['GAME_DATE'] = pd.to_datetime(schedule_df['GAME_DATE'])
    
    # Load all models
    models = {}
    model_features = {} # Store expected features per model
    for name, mfile in MODEL_FILES.items():
        saved_data = joblib.load(mfile)
        models[name] = saved_data['model']
        model_features[name] = saved_data['features']
    
    master_df = pd.read_parquet(MASTER_FILE)
    # Get team-level defensive stats from the master dataset to map onto upcoming games
    opp_stats_df = master_df[['OPP_TEAM_ID', 'SEASON_ID', 'OPP_PACE', 'OPP_DEF_RATING', 'OPP_EFG_PCT', 'OPP_TM_TOV_PCT', 'OPP_DREB_PCT']].drop_duplicates()
    
    active_players = get_active_rotational_players()
    
    print(f"Generating projections for the next upcoming game for all teams.")
    upcoming_window = schedule_df.copy()
    
    # Get teams playing in this window
    teams_playing = set(upcoming_window['HOME_TEAM'].unique()).union(set(upcoming_window['AWAY_TEAM'].unique()))
    print(f"Found {len(teams_playing)} teams playing remaining games.")
    
    # Build lookup dictionary for player's raw data
    all_projections = []
    
    # Due to API limits, we'll only do it for a few test players or we'll get timed out grabbing their live logs
    # For a real pipeline, we would map the 'teams_playing' to actual active players on that roster.
    # To prevent rate-limiting while demonstrating, let's limit to 10 random active players from these teams.
    
    # Let's map team abbreviation to team ID
    from nba_api.stats.static import teams
    nba_teams = teams.get_teams()
    abbr_to_id = {t['abbreviation']: t['id'] for t in nba_teams}
    teams_playing_ids = [abbr_to_id.get(t) for t in teams_playing if abbr_to_id.get(t)]
    
    # To accurately get a roster requires commonteamroster API which is also slow. 
    # For MVP performance without timeouts, let's use the local parquet files we already have.
    print("Finding players with cached local data who are playing soon...")
    local_files = os.listdir(DATA_DIR)
    player_ids_with_data = [int(f.split('_')[-2]) for f in local_files if f.endswith('_logs.parquet')]
    
    players_to_predict = [pid for pid in player_ids_with_data if pid in active_players]
    
    
    for count, pid in enumerate(players_to_predict):
        p_name = active_players[pid]
        
        # 1. Look up if they have an upcoming game
        # Need to map player to team. Without a roster API call, we'll assume they play if their LAST game's team is playing.
        p_file = os.path.join(DATA_DIR, f"{p_name.replace(' ', '_')}_{pid}_logs.parquet")
        raw_df = pd.read_parquet(p_file)
        if raw_df.empty: continue
        
        last_matchup = raw_df.iloc[-1]['MATCHUP']
        # Extract team they play FOR from the matchup (e.g. LAL @ BOS -> LAL)
        team_abbr = last_matchup.split(' ')[0]
        
        # Check if this team is playing in our window
        team_games = upcoming_window[(upcoming_window['HOME_TEAM'] == team_abbr) | (upcoming_window['AWAY_TEAM'] == team_abbr)]
        if team_games.empty:
            continue # No games soon
            
        next_game = team_games.iloc[0]
        opponent = next_game['AWAY_TEAM'] if next_game['HOME_TEAM'] == team_abbr else next_game['HOME_TEAM']
        format_matchup = f"{team_abbr} vs. {opponent}" if next_game['HOME_TEAM'] == team_abbr else f"{team_abbr} @ {opponent}"
        
        print(f"[{count+1}/{len(players_to_predict)}] Projecting {p_name} ({team_abbr}) vs {opponent} on {next_game['GAME_DATE'].date()}...")
        
        # 2. Append dummy row exactly like predict.py
        dummy_row = raw_df.iloc[-1:].copy()
        dummy_row['GAME_ID'] = str(next_game['GAME_ID'])
        dummy_row['GAME_DATE'] = next_game['GAME_DATE']
        dummy_row['MATCHUP'] = format_matchup
        
        combined_raw = pd.concat([raw_df, dummy_row], ignore_index=True)
        
        # 3. Engineer features
        engineered_df = engineered_features_for_player(combined_raw)
        engineered_df = engineered_df.sort_values('GAME_DATE')
        latest_game = engineered_df.iloc[-1].copy()
        
        # 4. Fill Feature dict
        features_list = [
            'B2B_FLAG', 'GAMES_LAST_7D',
            'ALTITUDE', 'HIGH_ALTITUDE_FLAG',
            'TRAVEL_DIST'
        ]
        
        # Add target features for all 4 targets
        for t in ['PTS', 'AST', 'REB', 'PRA']:
            features_list.extend([f'{t}_3g_avg', f'{t}_5g_avg', f'{t}_10g_avg'])
            
        feat_dict = {}
        for f in features_list:
            feat_dict[f] = latest_game.get(f, 0)
            
        # Add opponent defensive stats from Master table (if available)
        opp_feat = ['OPP_PACE', 'OPP_DEF_RATING', 'OPP_EFG_PCT', 'OPP_TM_TOV_PCT', 'OPP_DREB_PCT']
        for o_f in opp_feat:
            feat_dict[o_f] = latest_game.get(o_f, 0) # Usually these come out of the inner join in features.py if team_clusters exist
            
        travel_dir = latest_game.get('TRAVEL_DIR', 'None')
        tz_shift = latest_game.get('TZ_SHIFT', '0')
        opp_arch = latest_game.get('OPP_ARCHETYPE', 'None')
        
        feat_dict[f'TRAVEL_DIR_{travel_dir}'] = 1
        feat_dict[f'TZ_SHIFT_{tz_shift}'] = 1
        if pd.notna(opp_arch) and opp_arch != 'None':
            feat_dict[f'OPP_ARCHETYPE_{opp_arch}'] = 1
            
        # Re-initialize the base dataframe with all features
        X_pred = pd.DataFrame([feat_dict])
            
        # 5. Predict across all 4 models
        preds = {}
        for m_name, m_obj in models.items():
            expected_features = model_features[m_name]
            
            # Align with this specific model's expected columns
            X_model = X_pred.copy()
            for col in expected_features:
                if col not in X_model.columns:
                    X_model[col] = 0
            X_model = X_model[expected_features]
            
            preds[m_name] = float(m_obj.predict(X_model)[0])
            
        all_projections.append({
            'PLAYER_NAME': p_name,
            'TEAM': team_abbr,
            'OPPONENT': opponent,
            'GAME_DATE': next_game['GAME_DATE'].date(),
            'PREDICTED_PTS': round(preds.get('PTS', 0), 1),
            'PREDICTED_AST': round(preds.get('AST', 0), 1),
            'PREDICTED_REB': round(preds.get('REB', 0), 1),
            'PREDICTED_PRA': round(preds.get('PRA', 0), 1),
            'BASELINE_5G_PTS': round(feat_dict.get('PTS_5g_avg', 0), 1),
        })

    if all_projections:
        results_df = pd.DataFrame(all_projections)
        results_df = results_df.sort_values('PREDICTED_PTS', ascending=False)
        results_df.to_csv(PROJECTIONS_FILE, index=False)
        print(f"\nSuccessfully saved {len(results_df)} projections to {PROJECTIONS_FILE}")
        print("\nTop 5 Projections:")
        print(results_df.head().to_string(index=False))
    else:
        print("\nNo players had matches in the upcoming 3 days to project.")

if __name__ == "__main__":
    prepare_and_run_projections()
