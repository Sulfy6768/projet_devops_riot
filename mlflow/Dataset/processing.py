import pandas as pd
import os
from datetime import datetime

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
INPUT_CSV      = 'master_oracle_all_merged.csv'
OUTPUT_CSV     = 'master_clean_final.csv'

CHUNK_SIZE     = 50000                           # 30k–100k selon ta RAM
USEFUL_POSITIONS = ['team', 'top', 'jng', 'mid', 'bot', 'adc', 'sup', 'support']

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Début nettoyage chunké (CSV only)\n")

# ────────────────────────────────────────────────
# Fonction de nettoyage par chunk
# ────────────────────────────────────────────────
def clean_chunk(chunk):
    if 'date' in chunk.columns:
        chunk['date'] = pd.to_datetime(chunk['date'], errors='coerce')
    
    chunk['result'] = pd.to_numeric(chunk['result'], errors='coerce').astype('Int64')
    chunk['gameid'] = chunk['gameid'].astype(str)
    if 'participantid' in chunk.columns:
        chunk['participantid'] = chunk['participantid'].astype(str)
    
    # Positions utiles
    chunk = chunk[chunk['position'].isin(USEFUL_POSITIONS)].copy()
    
    # Drop lignes inutilisables
    chunk = chunk.dropna(subset=['gameid', 'date', 'result'], how='any')
    
    # Doublons locaux (pas parfait mais déjà bien)
    keys = [k for k in ['gameid', 'participantid'] if k in chunk.columns]
    if keys:
        chunk = chunk.drop_duplicates(subset=keys)
    
    return chunk

# ────────────────────────────────────────────────
# Traitement chunké + écriture CSV append
# ────────────────────────────────────────────────
print(f"Lecture par chunks de {CHUNK_SIZE:,} lignes...\n")

total_lines_read = 0
total_lines_kept = 0
chunk_count = 0
first_chunk = True

for chunk in pd.read_csv(INPUT_CSV, chunksize=CHUNK_SIZE, low_memory=False):
    chunk_count += 1
    lines_in = len(chunk)
    total_lines_read += lines_in
    
    print(f"Chunk {chunk_count:3d} : {lines_in:>8,} lignes lues")
    
    cleaned = clean_chunk(chunk)
    lines_out = len(cleaned)
    total_lines_kept += lines_out
    
    print(f"          → {lines_out:>8,} lignes conservées")
    
    # Écriture CSV en mode append
    if first_chunk:
        # Premier chunk → avec header
        cleaned.to_csv(OUTPUT_CSV, index=False, mode='w', encoding='utf-8')
        first_chunk = False
    else:
        # Chunks suivants → sans header, append
        cleaned.to_csv(OUTPUT_CSV, index=False, mode='a', header=False, encoding='utf-8')

print(f"\nTraitement terminé")
print(f"  Lignes lues   : {total_lines_read:,}")
print(f"  Lignes gardées: {total_lines_kept:,}")
print(f"  Chunks traités: {chunk_count}")
print(f"\nFichier créé : {OUTPUT_CSV}")
print(f"Taille approx : {os.path.getsize(OUTPUT_CSV) / 1_048_576:.1f} Mo")

print("\nTu peux maintenant ouvrir / continuer avec master_clean_final.csv")
print("Conseil : pour la suite, passe vite au .parquet pour éviter les ralentissements")
print("Exemple rapide pour vérifier :")
print("df = pd.read_csv('master_clean_final.csv', nrows=100)")
print("print(df['side'].value_counts(dropna=False))")