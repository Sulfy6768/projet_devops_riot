"""
Matchup Calculator - Calcule les scores de matchup basés sur notre dataset
Sans dépendance externe (pas de Lolalytics)
"""

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

DATA_PATH = "/app/data/master_dataset.csv"
CACHE_FILE = Path("/app/data/matchup_cache.json")

# Cache global
_matchup_cache: Optional[Dict] = None


def load_matchup_data() -> Dict:
    """
    Analyse le dataset pour extraire les matchups champion vs champion

    Retourne un dict: {
        "champion_A": {
            "vs": {
                "champion_B": {"wins": X, "games": Y, "winrate": Z}
            }
        }
    }
    """
    global _matchup_cache

    # Charger depuis le cache si disponible
    if _matchup_cache:
        return _matchup_cache

    try:
        if CACHE_FILE.exists():
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            _matchup_cache = data
            return _matchup_cache
    except Exception as e:
        print(f"Erreur chargement cache matchups: {e}")

    if not os.path.exists(DATA_PATH):
        print(f"Dataset not found at {DATA_PATH}")
        return {}

    print("Calcul des matchups depuis le dataset...")
    df = pd.read_csv(DATA_PATH)

    # Filtrer 2026
    df["year"] = pd.to_datetime(df["date"]).dt.year
    df = df[df["year"] >= 2026]

    if len(df) == 0:
        print("Pas de données 2026, utilisation de 2024+")
        df = pd.read_csv(DATA_PATH)
        df["year"] = pd.to_datetime(df["date"]).dt.year
        df = df[df["year"] >= 2024]

    matchups = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "games": 0}))

    pick_cols = ["pick1", "pick2", "pick3", "pick4", "pick5"]

    # Grouper par gameid pour avoir les deux équipes
    for game_id in df["gameid"].unique():
        game_rows = df[df["gameid"] == game_id]

        if len(game_rows) != 2:
            continue

        team1 = game_rows.iloc[0]
        team2 = game_rows.iloc[1]

        # Extraire les champions de chaque équipe
        def get_champions(row):
            champs = []
            for col in pick_cols:
                pick = row[col]
                if pd.notna(pick) and "." in str(pick):
                    parts = str(pick).split(".")
                    champs.append(
                        {"name": parts[0], "role": parts[1] if len(parts) > 1 else "unknown"}
                    )
            return champs

        team1_champs = get_champions(team1)
        team2_champs = get_champions(team2)

        team1_won = team1["result"] == 1

        # Pour chaque champion de l'équipe 1, enregistrer les matchups vs équipe 2
        for champ1 in team1_champs:
            for champ2 in team2_champs:
                key = f"{champ1['name']}_{champ1['role']}"
                vs_key = f"{champ2['name']}_{champ2['role']}"

                matchups[key][vs_key]["games"] += 1
                if team1_won:
                    matchups[key][vs_key]["wins"] += 1

        # Pareil pour équipe 2
        for champ2 in team2_champs:
            for champ1 in team1_champs:
                key = f"{champ2['name']}_{champ2['role']}"
                vs_key = f"{champ1['name']}_{champ1['role']}"

                matchups[key][vs_key]["games"] += 1
                if not team1_won:
                    matchups[key][vs_key]["wins"] += 1

    # Calculer les winrates
    result = {}
    for champ, vs_data in matchups.items():
        result[champ] = {"vs": {}}
        for vs_champ, stats in vs_data.items():
            if stats["games"] >= 5:  # Minimum 5 games pour être significatif
                winrate = stats["wins"] / stats["games"]
                result[champ]["vs"][vs_champ] = {
                    "wins": stats["wins"],
                    "games": stats["games"],
                    "winrate": round(winrate * 100, 1),
                }

    # Sauvegarder en cache
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(result), encoding="utf-8")
    except Exception as e:
        print(f"Erreur sauvegarde cache: {e}")

    _matchup_cache = result
    print(f"Matchups calculés pour {len(result)} champions")

    return result


def get_counter_score(champion: str, role: str, enemy_champions: List[str]) -> float:
    """
    Calcule un score de counter pour un champion contre une liste d'ennemis

    Args:
        champion: Le champion à évaluer (ex: "Yone")
        role: Le rôle (ex: "mid")
        enemy_champions: Liste des champions ennemis (ex: ["Jinx", "Thresh"])

    Returns:
        Score entre 0 et 100 (100 = excellent counter)
    """
    if not enemy_champions:
        return 50.0  # Score neutre

    matchups = load_matchup_data()

    # Mapper le rôle
    role_map = {
        "top": "top",
        "jng": "jng",
        "jungle": "jng",
        "mid": "mid",
        "middle": "mid",
        "bot": "bot",
        "adc": "bot",
        "bottom": "bot",
        "sup": "sup",
        "support": "sup",
        "utility": "sup",
    }
    normalized_role = role_map.get(role.lower(), role.lower())

    key = f"{champion}_{normalized_role}"

    if key not in matchups:
        # Essayer sans le rôle
        for k in matchups.keys():
            if k.startswith(f"{champion}_"):
                key = k
                break
        else:
            return 50.0  # Pas de données

    champ_matchups = matchups[key].get("vs", {})

    if not champ_matchups:
        return 50.0

    total_winrate = 0
    matched = 0

    for enemy in enemy_champions:
        # Chercher le matchup (n'importe quel rôle pour l'ennemi)
        for vs_key, stats in champ_matchups.items():
            if vs_key.startswith(f"{enemy}_"):
                total_winrate += stats["winrate"]
                matched += 1
                break

    if matched == 0:
        return 50.0

    avg_winrate = total_winrate / matched

    # Normaliser: 45% -> 0, 50% -> 50, 55% -> 100
    score = (avg_winrate - 45) * 10
    return max(0, min(100, score))


def get_blindpick_score(champion: str, role: str) -> float:
    """
    Calcule un score de blind pick (sécurité du pick)
    Un bon blind pick a des winrates stables contre la plupart des champions

    Returns:
        Score entre 0 et 100 (100 = très safe en blind)
    """
    matchups = load_matchup_data()

    # Mapper le rôle
    role_map = {
        "top": "top",
        "jng": "jng",
        "jungle": "jng",
        "mid": "mid",
        "middle": "mid",
        "bot": "bot",
        "adc": "bot",
        "bottom": "bot",
        "sup": "sup",
        "support": "sup",
        "utility": "sup",
    }
    normalized_role = role_map.get(role.lower(), role.lower())

    key = f"{champion}_{normalized_role}"

    if key not in matchups:
        for k in matchups.keys():
            if k.startswith(f"{champion}_"):
                key = k
                break
        else:
            return 50.0

    champ_matchups = matchups[key].get("vs", {})

    if not champ_matchups:
        return 60.0  # Pas de données = assez safe

    # Compter les matchups difficiles (WR < 45%)
    hard_counters = 0
    soft_counters = 0
    favorable = 0

    for vs_key, stats in champ_matchups.items():
        wr = stats["winrate"]
        if wr < 45:
            hard_counters += 1
        elif wr < 48:
            soft_counters += 1
        elif wr > 52:
            favorable += 1

    # Score: moins de counters = meilleur blind pick
    score = 70  # Base
    score -= hard_counters * 10
    score -= soft_counters * 3
    score += favorable * 2

    return max(0, min(100, score))


def get_best_counters(
    enemy_champions: List[str], role: str, top_n: int = 10
) -> List[Tuple[str, float]]:
    """
    Trouve les meilleurs counter-picks contre une équipe ennemie pour un rôle donné

    Returns:
        Liste de (champion, score) triée par score décroissant
    """
    matchups = load_matchup_data()

    role_map = {
        "top": "top",
        "jng": "jng",
        "jungle": "jng",
        "mid": "mid",
        "middle": "mid",
        "bot": "bot",
        "adc": "bot",
        "bottom": "bot",
        "sup": "sup",
        "support": "sup",
        "utility": "sup",
    }
    normalized_role = role_map.get(role.lower(), role.lower())

    scores = []

    # Pour chaque champion de ce rôle dans notre dataset
    for key in matchups.keys():
        if key.endswith(f"_{normalized_role}"):
            champion = key.replace(f"_{normalized_role}", "")
            score = get_counter_score(champion, role, enemy_champions)
            scores.append((champion, score))

    # Trier par score
    scores.sort(key=lambda x: x[1], reverse=True)

    return scores[:top_n]
