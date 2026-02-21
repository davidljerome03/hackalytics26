from nba_api.stats.static import players

nba_players = players.get_players()
for p in nba_players:
    if 'luka' in p['full_name'].lower():
        print(p)
