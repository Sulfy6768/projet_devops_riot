import pandas as pd
from tqdm import tqdm

# Charger le CSV clean
print("Chargement du fichier CSV...")
df = pd.read_csv('master_clean_final.csv', low_memory=False)

print("Shape initial:", df.shape)
print("Sides uniques:", df['side'].unique().tolist())
print("Positions uniques:", df['position'].unique().tolist())

# Groupby par gameid et side
grouped = df.groupby(['gameid', 'side'])
total_groups = len(grouped)
print(f"\nNombre de groupes à traiter: {total_groups}")

# Fonction pour enrichir une group (par side)
def enrich_team(group):
    # Séparer lignes roles vs team
    roles = group[group['position'] != 'team']
    team = group[group['position'] == 'team'].copy()
    
    if team.empty:
        return None  # Skip si pas de team
    
    # Dict champion → position (unique par side, ignore 'team')
    champ_to_pos = dict(zip(roles['champion'], roles['position']))
    
    # Cols pick (pick1, pick2, etc.)
    pick_cols = [col for col in team.columns if col.startswith('pick') and col[4:].isdigit()]
    
    # Remplacer chaque pickX par "champ.position"
    for col in pick_cols:
        team[col] = team[col].apply(lambda champ: f"{champ}.{champ_to_pos.get(champ, 'Unknown')}" if pd.notna(champ) else champ)
    
    return team

# Appliquer sur tous les groups avec barre de progression
print("\nEnrichissement des données...")
results = []
for name, group in tqdm(grouped, total=total_groups, desc="Traitement des équipes"):
    result = enrich_team(group)
    if result is not None:
        results.append(result)

enriched = pd.concat(results, ignore_index=True)

# Sauvegarde
print("\nSauvegarde du fichier...")
enriched.to_csv('master_enriched_team.csv', index=False)
print("  ✓ master_enriched_team.csv")

print("\nShape enriched:", enriched.shape)
print("Exemple de ligne enrichie (première team):")
print(enriched.head(1).T.to_string())

# Pour vérifier un game spécifique (de ton exemple)
example_game = 'LOLTMNT05_172024'
if example_game in enriched['gameid'].values:
    print("\nExemple pour game", example_game)
    print(enriched[enriched['gameid'] == example_game][['side', 'pick1', 'pick2', 'pick3', 'pick4', 'pick5']].to_string())
else:
    print("\nExemple game non trouvé → prends le premier du dataset pour tester")

print("\nFini ! Fichier 'master_enriched_team.csv' créé.")
print("Maintenant, ce fichier a les lignes team avec picks enrichis (ex: 'Corki.bot').")
print("Prochaine étape : pivot en wide (1 ligne/game) pour le modèle ? Ou autre chose ?")