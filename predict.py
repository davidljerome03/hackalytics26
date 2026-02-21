import os
import pandas as pd
import numpy as np
import joblib
from xgboost import XGBRegressor
from nba_api.stats.static import players

PROCESSED_DATA_DIR = "processed_data"
MASTER_FILE = os.path.join(PROCESSED_DATA_DIR, "master_dataset.parquet")
MODEL_FILE = os.path.join(PROCESSED_DATA_DIR, "xgb_pts_model.joblib")

def get_player_id(player_name):
    nba_players = players.get_players()
    # Try exact match first
    matched = [p for p in nba_players if p['full_name'].lower() == player_name.lower()]
    if matched:
        return matched[0]['id']
        
    # Try partial match if exact fails
    matched_partial = [p for p in nba_players if player_name.lower() in p['full_name'].lower()]
    if matched_partial:
        # Return the active one if possible
        for p in matched_partial:
            if p['is_active']:
                return p['id']
        # Fallback to the first match if none are active
        return matched_partial[0]['id']
        
    return None

def load_latest_features(player_id, df):
    """
    Get the most recent game for the player to use as the base for the next prediction.
    """
    player_df = df[df['PLAYER_ID'] == player_id].copy()
    if len(player_df) == 0:
        return None
        
    # Sort chronologically and get the very last row
    player_df = player_df.sort_values('GAME_DATE')
    latest_game = player_df.iloc[-1].copy()
    
    # We need to construct the feature vector expected by the model.
    # The model expects: PTS_3g_avg, PTS_5g_avg, PTS_10g_avg, B2B_FLAG, GAMES_LAST_7D, ALTITUDE, HIGH_ALTITUDE_FLAG, TRAVEL_DIST
    # + dummy columns for TRAVEL_DIR and TZ_SHIFT
    
    # Let's rebuild the rolling averages assuming the "latest game" is now history.
    # To predict the NEXT game, the "latest game" actual PTS becomes part of the trailing averages.
    # For a real system, you'd calculate this properly. For now, we'll just use the trailing averages from the latest game as a proxy 
    # (assuming the next game is similar to the last game's context in terms of rolling averages).
    
    # Extract just the features we need
    features = [
        'PTS_3g_avg', 'PTS_5g_avg', 'PTS_10g_avg',
        'B2B_FLAG', 'GAMES_LAST_7D',
        'ALTITUDE', 'HIGH_ALTITUDE_FLAG',
        'TRAVEL_DIST'
    ]
    
    # Dummy columns
    for col in df.columns:
        if col.startswith('TRAVEL_DIR_') or col.startswith('TZ_SHIFT_'):
            features.append(col)
            
    # Create the feature dict
    feat_dict = {}
    for f in features:
        # Default to 0 if the feature doesn't exist for some reason
        feat_dict[f] = latest_game.get(f, 0)
        
    # Convert to dataframe row
    return pd.DataFrame([feat_dict])


def train_and_save_model():
    """
    Trains the XGBoost model on all data and saves it to disk for quick predictions.
    """
    print("Training production model on complete dataset...")
    df = pd.read_parquet(MASTER_FILE)
    
    # This logic matches model.py prep_for_modeling
    cols_to_check = ['PTS', 'PTS_3g_avg', 'PTS_5g_avg', 'PTS_10g_avg']
    df_clean = df.dropna(subset=cols_to_check).copy()
    df_clean = pd.get_dummies(df_clean, columns=['TRAVEL_DIR', 'TZ_SHIFT'], drop_first=True)
    
    features = ['PTS_3g_avg', 'PTS_5g_avg', 'PTS_10g_avg', 'B2B_FLAG', 'GAMES_LAST_7D', 'ALTITUDE', 'HIGH_ALTITUDE_FLAG', 'TRAVEL_DIST']
    for col in df_clean.columns:
        if col.startswith('TRAVEL_DIR_') or col.startswith('TZ_SHIFT_'):
            features.append(col)
            
    df_clean = df_clean.dropna(subset=features)
    
    X = df_clean[features]
    y = df_clean['PTS']
    
    model = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42, n_jobs=-1)
    model.fit(X, y)
    
    # Save the model and the expected feature columns
    joblib.dump({'model': model, 'features': features}, MODEL_FILE)
    print(f"Model saved to {MODEL_FILE}")
    return model, features

def predict_player_points(player_name):
    # Load data
    if not os.path.exists(MASTER_FILE):
        print(f"File {MASTER_FILE} not found. You must run main.py first to build the dataset.")
        return
        
    df = pd.read_parquet(MASTER_FILE)
    # Apply dummy encoding immediately so load_latest_features can find them
    df = pd.get_dummies(df, columns=['TRAVEL_DIR', 'TZ_SHIFT'], drop_first=True)
    
    # Find player
    player_id = get_player_id(player_name)
    if not player_id:
        print(f"Could not find exact match for player: {player_name}")
        return
        
    # Try to load model, if it doesn't exist, train it
    if os.path.exists(MODEL_FILE):
        print("Loading existing model...")
        saved_data = joblib.load(MODEL_FILE)
        model = saved_data['model']
        expected_features = saved_data['features']
    else:
        model, expected_features = train_and_save_model()
        
    # Get player's latest features
    X_pred = load_latest_features(player_id, df)
    
    if X_pred is None:
        print(f"No valid historical data found for {player_name} to base a prediction on.")
        return
        
    # Ensure columns match what the model was trained on
    # Add missing dummy columns with 0
    for col in expected_features:
        if col not in X_pred.columns:
            X_pred[col] = 0
            
    # Order columns exactly as the model expects
    X_pred = X_pred[expected_features]
    
    # Predict
    prediction = model.predict(X_pred)[0]
    
    # Get their baseline (last 5 game average) for comparison
    baseline = X_pred['PTS_5g_avg'].iloc[0]
    
    print("\n" + "="*50)
    print(f" PREDICTION FOR: {player_name.upper()}")
    print("="*50)
    print(f" Baseline (Last 5 Games Avg): {baseline:.1f} PTS")
    print(f" XGBoost Model Prediction:    {prediction:.1f} PTS")
    print("="*50 + "\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        player = " ".join(sys.argv[1:])
        predict_player_points(player)
    else:
        print("Usage: python predict.py \"Player Name\"")
        print("Example: python predict.py \"LeBron James\"")
