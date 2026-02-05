"""
Champion Recommender - Recommande des picks basés sur les stats Lolalytics + masteries
Utilise uniquement Lolalytics pour les matchups et stats de champions
"""

from typing import Dict, List, Optional

# Import du scraper Lolalytics
try:
    from .lolalytics_scraper import (
        ROLE_MAP,
        get_blindpick_score,
        get_champion_stats,
        get_counter_score,
    )

    LOLALYTICS_ENABLED = True
    print("Lolalytics scraper loaded successfully")
except ImportError as e:
    LOLALYTICS_ENABLED = False
    print(f"Lolalytics scraper not available: {e}")
    ROLE_MAP = {"top": "top", "jng": "jungle", "mid": "middle", "bot": "bottom", "sup": "support"}

    def get_counter_score(champion: str, role: str, enemies: List[str]) -> float:
        return 50.0

    def get_blindpick_score(champion: str, role: str) -> float:
        return 50.0

    def get_champion_stats(champion: str, role: str) -> Dict:
        return {"winrate": 50.0, "games": 0}


def fetch_lolalytics_tierlist(role: str) -> List[Dict]:
    """
    Fonction placeholder - on n'utilise plus la tierlist
    Les recommandations sont basées sur les masteries du joueur
    """
    return []


def calculate_tier(winrate: float, pickrate: float = 5.0) -> str:
    """Calcule le tier d'un champion basé sur winrate"""
    # winrate en % (ex: 52.5)
    if winrate >= 53:
        return "S"
    elif winrate >= 51:
        return "A"
    elif winrate >= 49:
        return "B"
    elif winrate >= 47:
        return "C"
    else:
        return "D"


def get_recommendations(
    masteries: list,
    role: Optional[str] = None,
    top_n: int = 5,
    mastery_weight: float = 0.25,
    meta_weight: float = 0.30,
    counter_weight: float = 0.45,
    min_pickrate: float = 0.5,
    enemy_champions: Optional[List[str]] = None,
    ally_champions: Optional[List[str]] = None,
    banned_champions: Optional[List[str]] = None,
    mode: str = "balanced",
) -> list:
    """
    Recommande des champions basés sur les masteries du joueur + stats Lolalytics

    Approche:
    1. Prendre les champions que le joueur maîtrise (masteries)
    2. Récupérer leurs stats depuis Lolalytics (winrate, counters)
    3. Calculer un score combiné

    Args:
        masteries: Liste des masteries du joueur
        role: Rôle spécifique (top, jng, mid, bot, sup)
        enemy_champions: Champions ennemis déjà pickés
        mode: balanced, counter, blind, comfort
    """
    if not masteries:
        return []

    if not role:
        return []

    # Ajuster les poids selon le mode
    if mode == "counter" and enemy_champions:
        mastery_weight = 0.15
        meta_weight = 0.20
        counter_weight = 0.65
    elif mode == "blind":
        mastery_weight = 0.25
        meta_weight = 0.45
        counter_weight = 0.30
    elif mode == "comfort":
        mastery_weight = 0.55
        meta_weight = 0.25
        counter_weight = 0.20

    # Champions à exclure
    excluded = set()
    if enemy_champions:
        excluded.update([c.lower() for c in enemy_champions])
    if ally_champions:
        excluded.update([c.lower() for c in ally_champions])
    if banned_champions:
        excluded.update([c.lower() for c in banned_champions])

    # Normaliser les points de mastery
    max_points = max([m.get("champion_points", 0) for m in masteries]) if masteries else 1
    max_points = max(max_points, 1)

    recommendations = []

    # Parcourir les masteries du joueur (top 30 pour limiter les appels API)
    for mastery in masteries[:30]:
        champion = mastery.get("champion_name", "")

        if not champion:
            continue

        # Exclure les champions déjà pris ou bannis
        if champion.lower() in excluded:
            continue

        mastery_level = mastery.get("champion_level", 0)
        mastery_points = mastery.get("champion_points", 0)

        # Récupérer les stats Lolalytics pour ce champion
        if LOLALYTICS_ENABLED:
            stats = get_champion_stats(champion, role)
            winrate = stats.get("winrate", 50.0)
            pickrate = stats.get("pickrate", 0.0)
            games = stats.get("games", 0)

            # Filtrer les champions avec pickrate insuffisant sur cette lane
            if pickrate < min_pickrate:
                continue
        else:
            winrate = 50.0
            pickrate = 0.0
            games = 0

        # Score méta basé sur winrate Lolalytics
        meta_score = (winrate - 45) / 15  # Normalise 45-60% -> 0-1
        meta_score = max(0, min(1, meta_score))

        tier = calculate_tier(winrate)

        # Score mastery (0-1)
        mastery_score = 0
        if mastery_level > 0:
            mastery_score = min(mastery_level / 10, 0.7)
            mastery_score += (mastery_points / max_points) * 0.3

        # Score counter/blind
        counter_score_value = 0.5
        blindpick_score_value = 0.5

        if LOLALYTICS_ENABLED:
            if mode == "blind" or not enemy_champions:
                blindpick_score_value = get_blindpick_score(champion, role) / 100
                counter_score_value = blindpick_score_value
            elif enemy_champions:
                counter_score_value = get_counter_score(champion, role, enemy_champions) / 100

        # Score final
        if mode == "blind":
            final_score = (
                meta_score * meta_weight
                + mastery_score * mastery_weight
                + blindpick_score_value * counter_weight
            )
        else:
            final_score = (
                meta_score * meta_weight
                + mastery_score * mastery_weight
                + counter_score_value * counter_weight
            )

        # Bonus si bonne mastery + bon winrate
        if mastery_level >= 5 and winrate >= 51:
            final_score *= 1.10

        # Bonus pour les hard counters
        if counter_score_value >= 0.7 and enemy_champions:
            final_score *= 1.15

        # Générer la raison
        reasons = []

        if enemy_champions and counter_score_value >= 0.6:
            reasons.append(f"🎯 Counter vs {', '.join(enemy_champions[:2])}")
        elif mode == "blind" and blindpick_score_value >= 0.7:
            reasons.append("🛡️ Safe blind pick")

        if tier in ["S", "A"]:
            reasons.append(f"Tier {tier}")
        if winrate >= 52:
            reasons.append(f"{winrate:.1f}% WR")

        if mastery_level >= 7:
            reasons.append(f"M{mastery_level} ({mastery_points:,} pts)")
        elif mastery_level >= 5:
            reasons.append(f"M{mastery_level}")

        if not reasons:
            reasons.append("Pick solide")

        recommendations.append(
            {
                "champion": champion,
                "role": role,
                "score": round(final_score, 3),
                "winrate": round(winrate, 1),
                "pickrate": 0,  # Pas dispo sans tierlist
                "tier": tier,
                "mastery_level": mastery_level,
                "mastery_points": mastery_points,
                "counter_score": round(counter_score_value * 100, 1),
                "blindpick_score": round(blindpick_score_value * 100, 1)
                if mode == "blind"
                else None,
                "games_in_meta": games,
                "reason": " • ".join(reasons),
                "mode": mode,
            }
        )

    # Trier par score et prendre les top_n
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations[:top_n]


def get_meta_tierlist(role: Optional[str] = None) -> dict:
    """
    Retourne la tierlist - placeholder car l'endpoint tierlist ne fonctionne plus
    """
    return {}
