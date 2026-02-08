"""
Draft prediction and analysis routes.
"""

import time

from fastapi import APIRouter, HTTPException
from prometheus_client import Counter, Histogram

from .champions import CHAMPION_ID_TO_NAME, CHAMPIONS_BY_ROLE
from .models import DraftAnalyzeRequest, DraftPredictionRequest

router = APIRouter(prefix="/draft", tags=["draft"])

# ============================================
# Prometheus Metrics
# ============================================

DRAFT_PREDICTIONS_TOTAL = Counter(
    "draft_predictions_total",
    "Total number of draft predictions made",
    ["model_loaded"],
)
DRAFT_PREDICTION_LATENCY = Histogram(
    "draft_prediction_latency_seconds",
    "Latency of draft predictions",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)


# ============================================
# Draft Predictor (lazy loading)
# ============================================

_draft_predictor = None


def get_draft_predictor():
    """Load the draft prediction model (lazy loading)."""
    global _draft_predictor
    if _draft_predictor is None:
        try:
            import sys

            sys.path.insert(0, "/app/mlflow")
            from draft_predictor import DraftPredictor

            _draft_predictor = DraftPredictor(
                model_path="/app/mlflow/best_draft_transformer.pt",
                vocab_path="/app/mlflow/vocab.json",
            )
            print("✅ Draft Transformer model loaded!")
        except Exception as e:
            print(f"⚠️ Could not load Draft Transformer: {e}")
            _draft_predictor = "error"
    return _draft_predictor if _draft_predictor != "error" else None


# ============================================
# Routes
# ============================================


@router.post("/predict")
async def predict_draft_winrate(request: DraftPredictionRequest):
    """
    Predict draft winrate using the Transformer model.

    Pick format: "Champion.position" (ex: "Varus.bot", "Yone.mid")
    Bans are just champion names.
    """
    start_time = time.time()
    predictor = get_draft_predictor()

    if predictor is None:
        DRAFT_PREDICTIONS_TOTAL.labels(model_loaded="false").inc()
        DRAFT_PREDICTION_LATENCY.observe(time.time() - start_time)
        raise HTTPException(status_code=503, detail="Draft prediction model not loaded")

    try:
        # Le nouveau modèle utilise uniquement les picks (pas de bans)
        draft = {
            "blue_picks": [p for p in request.blue_picks if p],
            "red_picks": [p for p in request.red_picks if p],
        }

        blue_winrate = predictor.predict_win(draft)
        red_winrate = 1.0 - blue_winrate

        DRAFT_PREDICTIONS_TOTAL.labels(model_loaded="true").inc()
        DRAFT_PREDICTION_LATENCY.observe(time.time() - start_time)

        return {
            "blue_winrate": blue_winrate,
            "red_winrate": red_winrate,
            "confidence": (
                "high" if len(draft["blue_picks"]) >= 3 and len(draft["red_picks"]) >= 3 else "low"
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error predicting draft: {e}")
        DRAFT_PREDICTIONS_TOTAL.labels(model_loaded="error").inc()
        DRAFT_PREDICTION_LATENCY.observe(time.time() - start_time)
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post("/suggest")
async def suggest_champion(
    request: DraftPredictionRequest,
    position: int = 1,
    role: str = "mid",
    top_k: int = 5,
):
    """
    Suggest best champions for a position.

    position: 1-10 (1-5 for Blue picks, 6-10 for Red picks)
    role: top, jng, mid, bot, sup
    top_k: number of suggestions to return
    """
    predictor = get_draft_predictor()

    if predictor is None:
        raise HTTPException(status_code=503, detail="Draft prediction model not loaded")

    try:
        draft = {
            "blue_picks": [p for p in request.blue_picks if p],
            "red_picks": [p for p in request.red_picks if p],
        }

        suggestions = predictor.suggest_champion(
            draft,
            position_index=position,
            role=role.lower(),
            top_k=top_k,
            exclude_picked=True,
        )

        return {
            "suggestions": suggestions,
            "position": position,
            "role": role,
            "side": "Blue" if position <= 5 else "Red",
        }

    except Exception as e:
        print(f"Error suggesting champion: {e}")
        raise HTTPException(status_code=500, detail=f"Suggestion error: {str(e)}")


@router.post("/analyze")
async def analyze_draft(request: DraftAnalyzeRequest):
    """Analyze a draft and recommend champions based on player masteries."""
    from .riot_api import fetch_masteries_from_riot, get_puuid_from_riot_id

    recommendations = []

    for player in request.players:
        riot_id = player.get("riot_id", "")
        role = player.get("role", "").upper()

        if not riot_id or "#" not in riot_id:
            continue

        game_name, tag_line = riot_id.split("#", 1)

        # Get player masteries
        puuid = get_puuid_from_riot_id(game_name, tag_line)
        if not puuid:
            recommendations.append(
                {
                    "riot_id": riot_id,
                    "role": role,
                    "recommended_champions": [],
                    "error": "Player not found",
                }
            )
            continue

        raw_masteries = fetch_masteries_from_riot(puuid)
        if not raw_masteries:
            recommendations.append(
                {
                    "riot_id": riot_id,
                    "role": role,
                    "recommended_champions": [],
                    "error": "Masteries not available",
                }
            )
            continue

        # Transform masteries
        player_masteries = []
        for m in raw_masteries:
            champion_id = m.get("championId")
            player_masteries.append(
                {
                    "champion_id": champion_id,
                    "champion_name": CHAMPION_ID_TO_NAME.get(
                        champion_id, f"Champion_{champion_id}"
                    ),
                    "champion_level": m.get("championLevel", 0),
                    "champion_points": m.get("championPoints", 0),
                }
            )

        # Get role champions
        role_champions = set(CHAMPIONS_BY_ROLE.get(role, []))

        # Filter unavailable champions
        unavailable = set(
            request.banned_champions + request.picked_champions + request.enemy_champions
        )

        # Score champions
        scored_champions = []
        for mastery in player_masteries:
            champ_name = mastery["champion_name"]
            if champ_name in unavailable:
                continue

            is_role_champion = champ_name in role_champions
            score = mastery["champion_points"]
            if is_role_champion:
                score *= 2  # Bonus for role champions

            scored_champions.append(
                {
                    "champion_name": champ_name,
                    "champion_level": mastery["champion_level"],
                    "champion_points": mastery["champion_points"],
                    "score": score,
                    "is_role_champion": is_role_champion,
                    "playable": mastery["champion_points"] > 0,
                }
            )

        scored_champions.sort(key=lambda x: x["score"], reverse=True)

        # Keep only playable champions
        playable = [c for c in scored_champions if c["playable"]]
        if not playable:
            playable = scored_champions[:5]

        recommendations.append(
            {
                "riot_id": riot_id,
                "role": role,
                "recommended_champions": playable[:10],
                "total_masteries_found": len(player_masteries),
            }
        )

    return {
        "recommendations": recommendations,
        "banned": request.banned_champions,
        "picked": request.picked_champions,
        "enemy": request.enemy_champions,
    }
