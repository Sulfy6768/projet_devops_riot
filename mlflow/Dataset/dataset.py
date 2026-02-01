import pandas as pd
import glob
import os
from datetime import datetime

# ────────────────────────────────────────────────
# CONFIGURATION - À ADAPTER
# ────────────────────────────────────────────────
input_folder = '.'                          # ← Mets ton chemin ici si pas dans le dossier courant
# Exemples :
# input_folder = '/home/thomas/oracle_data'
# input_folder = 'C:/Users/Thomas/Documents/projet/oracle'

output_csv = 'master_oracle_all_merged.csv'

pattern = '*.csv'                           # ou '*_LoL_esports*.csv' pour être plus précis

# ────────────────────────────────────────────────
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Début de la fusion simple\n")
print(f"Dossier : {input_folder}\n")

files = sorted(glob.glob(os.path.join(input_folder, pattern)))

if not files:
    print("ERREUR : Aucun fichier CSV trouvé.")
    print("Vérifie le chemin et le pattern.")
    exit()

print(f"Trouvé {len(files)} fichiers :\n")
for f in files:
    print(f"  - {os.path.basename(f)}")

# ────────────────────────────────────────────────
print("\nLecture et fusion...")
dfs = []

for filepath in files:
    filename = os.path.basename(filepath)
    try:
        df = pd.read_csv(filepath, low_memory=False, encoding='utf-8')
        dfs.append(df)
        print(f"  lu : {filename} → {len(df):,} lignes")
    except Exception as e:
        print(f"  ERREUR sur {filename} → {e}")

if not dfs:
    print("\nAucun fichier n'a pu être lu → arrêt.")
    exit()

# ────────────────────────────────────────────────
print("\nConcaténation...")
master = pd.concat(dfs, ignore_index=True, sort=False)

print(f"\nDataset final : {len(master):,} lignes")
print(f"Colonnes : {len(master.columns)}")
print("Exemple des 5 premières colonnes :", master.columns[:5].tolist())

# ────────────────────────────────────────────────
print(f"\nSauvegarde dans {output_csv} ...")
try:
    master.to_csv(output_csv, index=False, encoding='utf-8')
    size_mb = os.path.getsize(output_csv) / 1_000_000
    print(f"✓ Fichier créé : {output_csv} ({size_mb:.1f} Mo)")
except Exception as e:
    print(f"Erreur lors de la sauvegarde : {e}")
    print("→ Essaie de fermer d'autres programmes pour libérer de la RAM")

print("\nTerminé !")
print("Tu peux maintenant ouvrir le CSV (attention : très gros fichier)")
print("Prochaines étapes : filtrer, nettoyer, extraire drafts, etc.")