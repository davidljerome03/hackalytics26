import os
import pandas as pd

PROCESSED_DATA_DIR = "processed_data"
CLUSTER_FILE = os.path.join(PROCESSED_DATA_DIR, "team_clusters.parquet")

def analyze_clusters():
    if not os.path.exists(CLUSTER_FILE):
        print("Cluster file not found. Please run team_clustering.py first.")
        return
        
    df = pd.read_parquet(CLUSTER_FILE)
    
    # We want to see the average stats for each archetype across all 4 seasons
    metrics = ['PACE', 'DEF_RATING', 'EFG_PCT', 'TM_TOV_PCT', 'OREB_PCT']
    
    # Check which metrics actually exist in the file
    available_metrics = [m for m in metrics if m in df.columns]
    
    print("\n" + "="*60)
    print(" DEFENSIVE ARCHETYPE ANALYSIS (2022-2026)")
    print("="*60)
    print("These are the 5 distinct defensive styles K-Means discovered:\n")
    
    # Calculate the league average for context
    league_avgs = df[available_metrics].mean()
    print("--- LEAGUE AVERAGES FOR CONTEXT ---")
    for metric in available_metrics:
        print(f"  {metric}: {league_avgs[metric]:.2f}")
    print("-" * 35 + "\n")
    
    # Group by Archetype and look at the averages
    cluster_means = df.groupby('OPP_ARCHETYPE')[available_metrics].mean()
    
    for archetype, row in cluster_means.iterrows():
        print(f"[{archetype}] PROFILE:")
        
        # Build a rough interpretation based on how this cluster compares to the league average
        style_notes = []
        if 'PACE' in row:
            if row['PACE'] > league_avgs['PACE'] + 1.5: style_notes.append("Fast-Paced (More Possessions)")
            elif row['PACE'] < league_avgs['PACE'] - 1.5: style_notes.append("Slow-Paced (Grinding Games)")
            
        if 'DEF_RATING' in row:
            # Lower def rating is BETTER defense
            if row['DEF_RATING'] < league_avgs['DEF_RATING'] - 1.5: style_notes.append("Elite Overall Defense")
            elif row['DEF_RATING'] > league_avgs['DEF_RATING'] + 1.5: style_notes.append("Poor Overall Defense")
            
        if 'TM_TOV_PCT' in row:
            if row['TM_TOV_PCT'] > league_avgs['TM_TOV_PCT'] + 0.5: style_notes.append("Aggressive (Forces Turnovers)")
            
        if not style_notes:
            style_notes.append("Average / Balanced Profile")
            
        print(f"  Interpretation: {', '.join(style_notes)}")
        
        # Print the raw stats for this cluster
        stats_list = []
        for m in available_metrics:
            if 'PCT' in m:
                stats_list.append(f"{m}: {row[m]:.3f}")
            else:
                stats_list.append(f"{m}: {row[m]:.1f}")
                
        stats_str = " | ".join(stats_list)
        print(f"  Stats: {stats_str}")
        
        # Show which teams from the CURRENT season (2025-26) belong to this archetype
        current_teams = df[(df['OPP_ARCHETYPE'] == archetype) & (df['SEASON'] == '2025-26')]['TEAM_NAME'].tolist()
        if current_teams:
            print(f"  2025-26 Teams in this Bucket: {', '.join(current_teams)}")
        else:
            print("  2025-26 Teams in this Bucket: None (This style was more common in past seasons)")
            
        print()

if __name__ == "__main__":
    analyze_clusters()
