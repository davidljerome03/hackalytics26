import os
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import joblib

DATA_DIR = "data"
PROCESSED_DATA_DIR = "processed_data"

if not os.path.exists(PROCESSED_DATA_DIR):
    os.makedirs(PROCESSED_DATA_DIR)

INPUT_FILE = os.path.join(DATA_DIR, "team_defensive_metrics.parquet")
OUTPUT_FILE = os.path.join(PROCESSED_DATA_DIR, "team_clusters.parquet")
SCALER_FILE = os.path.join(PROCESSED_DATA_DIR, "team_scaler.joblib")
KMEANS_FILE = os.path.join(PROCESSED_DATA_DIR, "team_kmeans.joblib")

def build_team_clusters():
    print("Loading Team Defensive Metrics...")
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found. Run team_ingestion.py first.")
        return
        
    df = pd.read_parquet(INPUT_FILE)
    
    # We want to cluster based on these specific defensive/style metrics
    # Note: Depending on the exact NBA API version, 'TM_TOV_PCT' might be 'TOV_PCT'
    # and we want Defensive Rebound % (DREB_PCT) to measure how well they finish defensive possessions.
    
    # Try to find the correct column names dynamically in case of slight API changes
    cols = df.columns.tolist()
    
    pace_col = 'PACE'
    def_rtg_col = 'DEF_RATING'
    efg_col = 'EFG_PCT' if 'EFG_PCT' in cols else 'EFG_PCT_ALLOWED'
    tov_col = 'TM_TOV_PCT' if 'TM_TOV_PCT' in cols else 'TOV_PCT'
    dreb_col = 'DREB_PCT' if 'DREB_PCT' in cols else 'REB_PCT'
    
    feature_cols = [pace_col, def_rtg_col, efg_col, tov_col, dreb_col]
    
    # Ensure all columns exist
    for c in feature_cols:
        if c not in cols:
            print(f"CRITICAL: Missing expected column {c} in team metrics!")
            print(f"Available columns: {cols}")
            return
            
    # Clean data (drop any rows missing these metrics)
    df_clean = df.dropna(subset=feature_cols).copy()
    
    print(f"Clustering {len(df_clean)} team-season records against {feature_cols}...")
    X = df_clean[feature_cols]
    
    # Scale the features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # KMeans Clustering (5 Archetypes)
    # E.g., Fast/Bad D, Slow/Elite D, Average/High Turnovers, etc.
    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    df_clean['OPP_ARCHETYPE'] = kmeans.fit_predict(X_scaled)
    
    # Map the Archetype IDs into string prefixes to easily dummy-encode later
    df_clean['OPP_ARCHETYPE'] = df_clean['OPP_ARCHETYPE'].apply(lambda x: f"Type_{x}")
    
    # Save the Models for predict.py
    joblib.dump(scaler, SCALER_FILE)
    joblib.dump(kmeans, KMEANS_FILE)
    print(f"Saved scaler to {SCALER_FILE}")
    print(f"Saved kmeans model to {KMEANS_FILE}")
    
    # Save the resulting dataframe (we only need the keys and the new features)
    output_df = df_clean[['TEAM_ID', 'TEAM_NAME', 'SEASON', 'OPP_ARCHETYPE'] + feature_cols]
    output_df.to_parquet(OUTPUT_FILE, index=False)
    
    print(f"\nSuccessfully clustered teams into 5 Defensive Archetypes.")
    print(f"Saved team archetype map to {OUTPUT_FILE}")
    
    # Quick sanity check on the clusters
    print("\nCluster Center Averages:")
    summary = output_df.groupby('OPP_ARCHETYPE')[feature_cols].mean()
    print(summary)

if __name__ == "__main__":
    build_team_clusters()
