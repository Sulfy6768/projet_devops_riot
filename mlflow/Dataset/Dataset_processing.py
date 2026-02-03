"""
Pipeline de traitement des datasets League of Legends
=====================================================

Ce script traite les fichiers CSV d'Oracle's Elixir en 3 étapes :

1. EXTRACTION : Garde uniquement les colonnes utiles de chaque CSV
2. ENRICHISSEMENT : Associe chaque pick à sa position (ex: "Corki" → "Corki.bot")
3. FUSION : Combine tous les CSV traités en un seul dataset final

Structure des dossiers :
- Dataset/Imutable/    → CSV originaux (NE PAS MODIFIER)
- Dataset/Processing/  → CSV temporaires pendant le traitement
- Dataset/             → Dataset final (master_dataset.csv)

Usage :
    python processing.py
"""

import pandas as pd
import glob
import os
from tqdm import tqdm
import shutil

# ============================================
# CONFIGURATION
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMUTABLE_DIR = os.path.join(BASE_DIR, "Immutable")
PROCESSING_DIR = os.path.join(BASE_DIR, "Processing")
OUTPUT_FILE = os.path.join(BASE_DIR, "master_dataset.csv")

# Colonnes à conserver (en minuscules pour la normalisation)
COLUMNS_TO_KEEP = [
    "gameid",
    "date",
    "side",
    "position",
    "firstpick",
    "champion",
    "ban1",
    "ban2",
    "ban3",
    "ban4",
    "ban5",
    "pick1",
    "pick2",
    "pick3",
    "pick4",
    "pick5",
    "result",
]


# ============================================
# ÉTAPE 1 : EXTRACTION DES COLONNES
# ============================================
def extract_columns(input_path, output_path):
    """
    Lit un CSV et ne garde que les colonnes utiles.
    Gère les variations de noms de colonnes (ex: firstPick vs firstpick).
    """
    df = pd.read_csv(input_path, low_memory=False)

    # Normaliser les noms de colonnes en minuscules
    df.columns = df.columns.str.lower()

    # Garder uniquement les colonnes qui existent
    cols_present = [col for col in COLUMNS_TO_KEEP if col in df.columns]

    if not cols_present:
        print(f"  ⚠️ Aucune colonne utile trouvée dans {os.path.basename(input_path)}")
        return None

    df_filtered = df[cols_present].copy()
    df_filtered.to_csv(output_path, index=False)

    return len(df_filtered)


# ============================================
# COLONNES OBLIGATOIRES (ne pas garder si vides)
# ============================================
REQUIRED_COLUMNS = [
    "gameid",
    "side",
    "ban1",
    "ban2",
    "ban3",
    "ban4",
    "ban5",
    "pick1",
    "pick2",
    "pick3",
    "pick4",
    "pick5",
    "result",
]


# ============================================
# ÉTAPE 2 : ENRICHISSEMENT DES PICKS
# ============================================
def enrich_picks(df):
    """
    Pour chaque équipe (side), associe le champion pické à sa position.
    Transforme "Corki" en "Corki.bot" par exemple.

    Retourne uniquement les lignes où position == "team".
    Filtre les parties sans picks complets.
    """
    # Grouper par game et side
    grouped = df.groupby(["gameid", "side"])

    results = []
    skipped_count = 0

    for (game_id, side), group in tqdm(grouped, desc="  Enrichissement", leave=False):
        # Séparer les lignes joueurs (positions) et la ligne team
        players = group[group["position"] != "team"]
        team = group[group["position"] == "team"].copy()

        if team.empty:
            skipped_count += 1
            continue

        # Vérifier que toutes les colonnes obligatoires sont présentes et non vides
        row = team.iloc[0]
        is_valid = True
        for col in REQUIRED_COLUMNS:
            if col in team.columns:
                if pd.isna(row[col]) or str(row[col]).strip() == "":
                    is_valid = False
                    break
            else:
                is_valid = False
                break

        if not is_valid:
            skipped_count += 1
            continue

        # Créer le mapping champion → position
        champ_to_pos = dict(zip(players["champion"], players["position"]))

        # Colonnes de picks
        pick_cols = ["pick1", "pick2", "pick3", "pick4", "pick5"]

        # Enrichir chaque pick avec sa position
        for col in pick_cols:
            if col in team.columns:
                team[col] = team[col].apply(
                    lambda champ: (
                        f"{champ}.{champ_to_pos.get(champ, 'unknown')}"
                        if pd.notna(champ)
                        else champ
                    )
                )

        results.append(team)

    if skipped_count > 0:
        print(f"    ⚠️ {skipped_count} équipes ignorées (données manquantes)")

    if not results:
        return pd.DataFrame()

    return pd.concat(results, ignore_index=True)


# ============================================
# PIPELINE PRINCIPALE
# ============================================
def run_pipeline():
    """
    Exécute la pipeline complète de traitement.
    """
    print("=" * 60)
    print("PIPELINE DE TRAITEMENT DES DATASETS")
    print("=" * 60)

    # Vérifier que le dossier Imutable existe
    if not os.path.exists(IMUTABLE_DIR):
        print(f"\n❌ ERREUR : Le dossier '{IMUTABLE_DIR}' n'existe pas.")
        print("   Créez-le et placez-y vos fichiers CSV originaux.")
        return

    # Créer/nettoyer le dossier Processing
    if os.path.exists(PROCESSING_DIR):
        shutil.rmtree(PROCESSING_DIR)
    os.makedirs(PROCESSING_DIR)

    # Lister les fichiers CSV dans Imutable
    csv_files = sorted(glob.glob(os.path.join(IMUTABLE_DIR, "*.csv")))

    if not csv_files:
        print(f"\n❌ ERREUR : Aucun fichier CSV trouvé dans '{IMUTABLE_DIR}'")
        return

    print(f"\n📁 Fichiers trouvés : {len(csv_files)}")
    for f in csv_files:
        print(f"   - {os.path.basename(f)}")

    # ─────────────────────────────────────────
    # ÉTAPE 1 : Extraction des colonnes
    # ─────────────────────────────────────────
    print("\n" + "─" * 60)
    print("ÉTAPE 1 : Extraction des colonnes utiles")
    print("─" * 60)

    for filepath in csv_files:
        filename = os.path.basename(filepath)
        output_path = os.path.join(PROCESSING_DIR, f"extracted_{filename}")

        rows = extract_columns(filepath, output_path)
        if rows:
            print(f"  ✓ {filename} → {rows:,} lignes")

    # ─────────────────────────────────────────
    # ÉTAPE 2 : Enrichissement des picks
    # ─────────────────────────────────────────
    print("\n" + "─" * 60)
    print("ÉTAPE 2 : Enrichissement des picks (champion.position)")
    print("─" * 60)

    extracted_files = sorted(glob.glob(os.path.join(PROCESSING_DIR, "extracted_*.csv")))

    for filepath in extracted_files:
        filename = os.path.basename(filepath)

        # Charger le fichier extrait
        df = pd.read_csv(filepath, low_memory=False)

        # Enrichir les picks
        df_enriched = enrich_picks(df)

        if df_enriched.empty:
            print(f"  ⚠️ {filename} → Aucune donnée team")
            continue

        # Sauvegarder
        output_name = filename.replace("extracted_", "enriched_")
        output_path = os.path.join(PROCESSING_DIR, output_name)
        df_enriched.to_csv(output_path, index=False)

        print(f"  ✓ {filename} → {len(df_enriched):,} lignes team")

    # ─────────────────────────────────────────
    # ÉTAPE 3 : Fusion en un seul fichier
    # ─────────────────────────────────────────
    print("\n" + "─" * 60)
    print("ÉTAPE 3 : Fusion des fichiers enrichis")
    print("─" * 60)

    enriched_files = sorted(glob.glob(os.path.join(PROCESSING_DIR, "enriched_*.csv")))

    if not enriched_files:
        print("  ❌ Aucun fichier enrichi à fusionner")
        return

    print(f"  Fusion de {len(enriched_files)} fichiers...")

    dfs = []
    for filepath in enriched_files:
        df = pd.read_csv(filepath, low_memory=False)
        dfs.append(df)
        print(f"    + {os.path.basename(filepath)} ({len(df):,} lignes)")

    master = pd.concat(dfs, ignore_index=True)

    # Supprimer la colonne "champion" (plus utile après enrichissement)
    if "champion" in master.columns:
        master = master.drop(columns=["champion"])
        print("  ✓ Colonne 'champion' supprimée")

    if "position" in master.columns:
        master = master.drop(columns=["position"])
        print("  ✓ Colonne 'position' supprimée")

    # Trier par date si disponible
    if "date" in master.columns:
        master = master.sort_values("date").reset_index(drop=True)

    # Sauvegarder le fichier final
    master.to_csv(OUTPUT_FILE, index=False)

    # ─────────────────────────────────────────
    # RÉSUMÉ
    # ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ PIPELINE TERMINÉE")
    print("=" * 60)

    file_size_mb = os.path.getsize(OUTPUT_FILE) / 1_048_576
    print(f"\n📊 Dataset final : {OUTPUT_FILE}")
    print(f"   - Taille    : {file_size_mb:.1f} Mo")
    print(f"   - Lignes    : {len(master):,}")
    print(f"   - Colonnes  : {list(master.columns)}")
    print(f"   - Games     : {master['gameid'].nunique():,}")

    # Distribution des victoires par side
    if "result" in master.columns and "side" in master.columns:
        print("\n📈 Distribution des victoires :")
        for side in ["Blue", "Red"]:
            side_df = master[master["side"] == side]
            if len(side_df) > 0:
                winrate = side_df["result"].mean() * 100
                print(f"   - {side} : {winrate:.1f}% winrate ({len(side_df):,} games)")

    # Afficher un exemple
    print("\n📋 Exemple de lignes :")
    sample_cols = ["gameid", "side", "pick1", "pick2", "pick3", "result"]
    sample_cols = [c for c in sample_cols if c in master.columns]
    print(master[sample_cols].head(4).to_string(index=False))

    # Supprimer les fichiers temporaires
    print(f"\n🗑️  Suppression des fichiers temporaires...")
    shutil.rmtree(PROCESSING_DIR)
    print(f"   ✓ Dossier '{PROCESSING_DIR}' supprimé")


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    run_pipeline()
