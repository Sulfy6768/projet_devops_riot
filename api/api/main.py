"""
Riot Stats API - Backend FastAPI
Gestion des utilisateurs, masteries et statistiques
"""

import hashlib
import json
import os
import time
from typing import Optional
from urllib.parse import unquote

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.lolalytics_scraper import get_champion_stats
from api.recommender import get_meta_tierlist, get_recommendations

app = FastAPI(title="Riot Stats API", version="1.0.0")

# CORS pour le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")
RIOT_REGION = os.getenv("RIOT_REGION", "euw1")
DATA_DIR = "/app/data"
USERS_FILE = f"{DATA_DIR}/users.json"
MASTERIES_FILE = f"{DATA_DIR}/masteries.json"

# Créer le dossier data s'il n'existe pas
os.makedirs(DATA_DIR, exist_ok=True)

# ============================================
# Modèles Pydantic
# ============================================


class UserRegister(BaseModel):
    riot_id: str  # Format: GameName#TagLine
    password: str


class UserLogin(BaseModel):
    riot_id: str
    password: str


class UserResponse(BaseModel):
    riot_id: str
    puuid: Optional[str] = None
    region: str = "euw1"


class MasteryData(BaseModel):
    champion_id: int
    champion_name: str
    champion_level: int
    champion_points: int
    last_play_time: Optional[int] = None


# ============================================
# Fonctions utilitaires
# ============================================


def load_json(filepath: str) -> dict:
    """Charge un fichier JSON, retourne {} si n'existe pas"""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return {}


def save_json(filepath: str, data: dict):
    """Sauvegarde un fichier JSON"""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def hash_password(password: str) -> str:
    """Hash un mot de passe avec SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_routing(region: str) -> str:
    """Retourne le routing régional pour les endpoints Riot"""
    routing_map = {
        "euw1": "europe",
        "eun1": "europe",
        "tr1": "europe",
        "ru": "europe",
        "na1": "americas",
        "br1": "americas",
        "la1": "americas",
        "la2": "americas",
        "kr": "asia",
        "jp1": "asia",
        "oc1": "sea",
        "ph2": "sea",
        "sg2": "sea",
        "th2": "sea",
        "tw2": "sea",
        "vn2": "sea",
    }
    return routing_map.get(region, "europe")


def get_puuid_from_riot_id(game_name: str, tag_line: str) -> Optional[str]:
    """Récupère le PUUID depuis un Riot ID"""
    if not RIOT_API_KEY:
        return None

    routing = get_routing(RIOT_REGION)
    url = f"https://{routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("puuid")
    except Exception as e:
        print(f"Error getting PUUID: {e}")
    return None


def get_summoner_id_from_puuid(puuid: str) -> Optional[str]:
    """Récupère le Summoner ID depuis un PUUID"""
    if not RIOT_API_KEY:
        return None

    url = f"https://{RIOT_REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("id")
    except Exception as e:
        print(f"Error getting Summoner ID: {e}")
    return None


def fetch_masteries_from_riot(puuid: str) -> list:
    """Récupère les masteries depuis l'API Riot"""
    if not RIOT_API_KEY:
        return []

    # Utiliser l'endpoint v4 avec le PUUID
    url = f"https://{RIOT_REGION}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching masteries: {e}")
    return []


# Mapping champion ID -> Name (simplifié, à compléter)
CHAMPION_NAMES = {
    1: "Annie",
    2: "Olaf",
    3: "Galio",
    4: "TwistedFate",
    5: "XinZhao",
    6: "Urgot",
    7: "LeBlanc",
    8: "Vladimir",
    9: "Fiddlesticks",
    10: "Kayle",
    11: "MasterYi",
    12: "Alistar",
    13: "Ryze",
    14: "Sion",
    15: "Sivir",
    16: "Soraka",
    17: "Teemo",
    18: "Tristana",
    19: "Warwick",
    20: "Nunu",
    21: "MissFortune",
    22: "Ashe",
    23: "Tryndamere",
    24: "Jax",
    25: "Morgana",
    26: "Zilean",
    27: "Singed",
    28: "Evelynn",
    29: "Twitch",
    30: "Karthus",
    31: "ChoGath",
    32: "Amumu",
    33: "Rammus",
    34: "Anivia",
    35: "Shaco",
    36: "DrMundo",
    37: "Sona",
    38: "Kassadin",
    39: "Irelia",
    40: "Janna",
    41: "Gangplank",
    42: "Corki",
    43: "Karma",
    44: "Taric",
    45: "Veigar",
    48: "Trundle",
    50: "Swain",
    51: "Caitlyn",
    53: "Blitzcrank",
    54: "Malphite",
    55: "Katarina",
    56: "Nocturne",
    57: "Maokai",
    58: "Renekton",
    59: "JarvanIV",
    60: "Elise",
    61: "Orianna",
    62: "MonkeyKing",
    63: "Brand",
    64: "LeeSin",
    67: "Vayne",
    68: "Rumble",
    69: "Cassiopeia",
    72: "Skarner",
    74: "Heimerdinger",
    75: "Nasus",
    76: "Nidalee",
    77: "Udyr",
    78: "Poppy",
    79: "Gragas",
    80: "Pantheon",
    81: "Ezreal",
    82: "Mordekaiser",
    83: "Yorick",
    84: "Akali",
    85: "Kennen",
    86: "Garen",
    89: "Leona",
    90: "Malzahar",
    91: "Talon",
    92: "Riven",
    96: "KogMaw",
    98: "Shen",
    99: "Lux",
    101: "Xerath",
    102: "Shyvana",
    103: "Ahri",
    104: "Graves",
    105: "Fizz",
    106: "Volibear",
    107: "Rengar",
    110: "Varus",
    111: "Nautilus",
    112: "Viktor",
    113: "Sejuani",
    114: "Fiora",
    115: "Ziggs",
    117: "Lulu",
    119: "Draven",
    120: "Hecarim",
    121: "KhaZix",
    122: "Darius",
    126: "Jayce",
    127: "Lissandra",
    131: "Diana",
    133: "Quinn",
    134: "Syndra",
    136: "AurelionSol",
    141: "Kayn",
    142: "Zoe",
    143: "Zyra",
    145: "KaiSa",
    147: "Seraphine",
    150: "Gnar",
    154: "Zac",
    157: "Yasuo",
    161: "VelKoz",
    163: "Taliyah",
    164: "Camille",
    166: "Akshan",
    200: "BelVeth",
    201: "Braum",
    202: "Jhin",
    203: "Kindred",
    221: "Zeri",
    222: "Jinx",
    223: "TahmKench",
    233: "Briar",
    234: "Viego",
    235: "Senna",
    236: "Lucian",
    238: "Zed",
    240: "Kled",
    245: "Ekko",
    246: "Qiyana",
    254: "Vi",
    266: "Aatrox",
    267: "Nami",
    268: "Azir",
    350: "Yuumi",
    360: "Samira",
    412: "Thresh",
    420: "Illaoi",
    421: "RekSai",
    427: "Ivern",
    429: "Kalista",
    432: "Bard",
    497: "Rakan",
    498: "Xayah",
    516: "Ornn",
    517: "Sylas",
    518: "Neeko",
    523: "Aphelios",
    526: "Rell",
    555: "Pyke",
    711: "Vex",
    777: "Yone",
    875: "Sett",
    876: "Lillia",
    887: "Gwen",
    888: "Renata",
    895: "Nilah",
    897: "KSante",
    901: "Smolder",
    902: "Milio",
    910: "Hwei",
    950: "Naafiri",
    893: "Aurora",
    903: "Ambessa",
    904: "Zaahen",
}

# ============================================
# Routes API
# ============================================


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "riot-api"}


@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserRegister):
    """Inscription d'un nouvel utilisateur"""
    users = load_json(USERS_FILE)

    # Vérifier si l'utilisateur existe déjà
    if user.riot_id in users:
        raise HTTPException(status_code=400, detail="Utilisateur déjà existant")

    # Parser le Riot ID
    if "#" not in user.riot_id:
        raise HTTPException(status_code=400, detail="Format invalide. Utilisez: GameName#TagLine")

    game_name, tag_line = user.riot_id.rsplit("#", 1)

    # Récupérer le PUUID depuis riot
    puuid = get_puuid_from_riot_id(game_name, tag_line)

    # Créer l'utilisateur
    users[user.riot_id] = {
        "password_hash": hash_password(user.password),
        "puuid": puuid,
        "region": RIOT_REGION,
        "created_at": int(time.time()),
    }
    save_json(USERS_FILE, users)

    # Récupérer et sauvegarder les masteries
    if puuid:
        await update_user_masteries(user.riot_id, puuid)

    return UserResponse(riot_id=user.riot_id, puuid=puuid, region=RIOT_REGION)


@app.post("/auth/login", response_model=UserResponse)
async def login(user: UserLogin):
    """Connexion d'un utilisateur"""
    users = load_json(USERS_FILE)

    if user.riot_id not in users:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")

    stored_user = users[user.riot_id]
    if stored_user["password_hash"] != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")

    puuid = stored_user.get("puuid")

    # Mettre à jour les masteries à chaque login
    if puuid:
        await update_user_masteries(user.riot_id, puuid)

    return UserResponse(
        riot_id=user.riot_id, puuid=puuid, region=stored_user.get("region", RIOT_REGION)
    )


async def update_user_masteries(riot_id: str, puuid: str):
    """Met à jour les masteries d'un utilisateur"""
    masteries_data = load_json(MASTERIES_FILE)

    # Récupérer les masteries depuis Riot
    raw_masteries = fetch_masteries_from_riot(puuid)

    # Transformer les données
    masteries = []
    for m in raw_masteries:
        champion_id = m.get("championId")
        masteries.append(
            {
                "champion_id": champion_id,
                "champion_name": CHAMPION_NAMES.get(champion_id, f"Champion_{champion_id}"),
                "champion_level": m.get("championLevel", 0),
                "champion_points": m.get("championPoints", 0),
                "last_play_time": m.get("lastPlayTime"),
            }
        )

    # Sauvegarder
    masteries_data[riot_id] = {
        "puuid": puuid,
        "masteries": masteries,
        "updated_at": int(time.time()),
    }
    save_json(MASTERIES_FILE, masteries_data)


@app.get("/masteries/{riot_id}")
async def get_masteries(riot_id: str):
    """Récupère les masteries d'un utilisateur"""
    riot_id = unquote(riot_id)  # Décode %20 -> espace, %23 -> #
    masteries_data = load_json(MASTERIES_FILE)

    if riot_id not in masteries_data:
        raise HTTPException(status_code=404, detail="Masteries non trouvées")

    return masteries_data[riot_id]


@app.get("/masteries/{riot_id}/top")
async def get_top_masteries(riot_id: str, limit: int = 10):
    """Récupère les top masteries d'un utilisateur"""
    riot_id = unquote(riot_id)  # Décode %20 -> espace, %23 -> #
    masteries_data = load_json(MASTERIES_FILE)

    if riot_id not in masteries_data:
        raise HTTPException(status_code=404, detail="Masteries non trouvées")

    masteries = masteries_data[riot_id].get("masteries", [])
    # Trier par points décroissants
    sorted_masteries = sorted(masteries, key=lambda x: x["champion_points"], reverse=True)

    return {"masteries": sorted_masteries[:limit]}


@app.get("/users/{riot_id}")
async def get_user(riot_id: str):
    """Récupère les infos d'un utilisateur"""
    riot_id = unquote(riot_id)  # Décode %20 -> espace, %23 -> #
    users = load_json(USERS_FILE)

    if riot_id not in users:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    user = users[riot_id]
    return UserResponse(
        riot_id=riot_id, puuid=user.get("puuid"), region=user.get("region", RIOT_REGION)
    )


@app.post("/masteries/{riot_id}/refresh")
async def refresh_masteries(riot_id: str):
    """Force le rafraîchissement des masteries"""
    riot_id = unquote(riot_id)  # Décode %20 -> espace, %23 -> #
    users = load_json(USERS_FILE)

    if riot_id not in users:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    puuid = users[riot_id].get("puuid")
    if not puuid:
        raise HTTPException(status_code=400, detail="PUUID non disponible")

    await update_user_masteries(riot_id, puuid)

    return {"message": "Masteries mises à jour"}


@app.get("/masteries/lookup/{game_name}/{tag_line}")
async def lookup_masteries(game_name: str, tag_line: str, limit: int = 50):
    """Récupère les masteries d'un joueur directement via son Riot ID (sans compte)"""

    # Récupérer le PUUID
    puuid = get_puuid_from_riot_id(game_name, tag_line)
    if not puuid:
        raise HTTPException(status_code=404, detail="Joueur non trouvé")

    # Récupérer les masteries
    raw_masteries = fetch_masteries_from_riot(puuid)
    if not raw_masteries:
        raise HTTPException(status_code=404, detail="Masteries non disponibles")

    # Transformer les données
    masteries = []
    for m in raw_masteries[:limit]:
        champion_id = m.get("championId")
        masteries.append(
            {
                "champion_id": champion_id,
                "champion_name": CHAMPION_NAMES.get(champion_id, f"Champion_{champion_id}"),
                "champion_level": m.get("championLevel", 0),
                "champion_points": m.get("championPoints", 0),
            }
        )

    return {"riot_id": f"{game_name}#{tag_line}", "puuid": puuid, "masteries": masteries}


# ============================================
# Analyse de Draft - Recommandations
# ============================================

# Rôles possibles
ROLES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

# Champions par rôle
CHAMPIONS_BY_ROLE = {
    "TOP": [
        "Aatrox",
        "Camille",
        "Darius",
        "Fiora",
        "Gangplank",
        "Garen",
        "Gnar",
        "Gwen",
        "Illaoi",
        "Irelia",
        "Jax",
        "Jayce",
        "KSante",
        "Kayle",
        "Kennen",
        "Kled",
        "Malphite",
        "Mordekaiser",
        "Nasus",
        "Olaf",
        "Ornn",
        "Pantheon",
        "Poppy",
        "Quinn",
        "Renekton",
        "Riven",
        "Rumble",
        "Sett",
        "Shen",
        "Singed",
        "Sion",
        "Teemo",
        "Trundle",
        "Tryndamere",
        "Urgot",
        "Vayne",
        "Volibear",
        "Yorick",
    ],
    "JUNGLE": [
        "Amumu",
        "BelVeth",
        "Briar",
        "Diana",
        "Ekko",
        "Elise",
        "Evelynn",
        "Fiddlesticks",
        "Gragas",
        "Graves",
        "Hecarim",
        "Ivern",
        "JarvanIV",
        "Karthus",
        "Kayn",
        "KhaZix",
        "Kindred",
        "LeeSin",
        "Lillia",
        "MasterYi",
        "Naafiri",
        "Nidalee",
        "Nocturne",
        "Nunu",
        "Olaf",
        "Poppy",
        "Rammus",
        "RekSai",
        "Rengar",
        "Sejuani",
        "Shaco",
        "Shyvana",
        "Skarner",
        "Taliyah",
        "Udyr",
        "Vi",
        "Viego",
        "Volibear",
        "Warwick",
        "MonkeyKing",
        "XinZhao",
        "Zac",
    ],
    "MIDDLE": [
        "Ahri",
        "Akali",
        "Akshan",
        "Anivia",
        "Annie",
        "AurelionSol",
        "Azir",
        "Brand",
        "Cassiopeia",
        "Corki",
        "Diana",
        "Ekko",
        "Fizz",
        "Galio",
        "Hwei",
        "Irelia",
        "Kassadin",
        "Katarina",
        "LeBlanc",
        "Lissandra",
        "Lux",
        "Malzahar",
        "Naafiri",
        "Neeko",
        "Orianna",
        "Pantheon",
        "Qiyana",
        "Ryze",
        "Sylas",
        "Syndra",
        "Talon",
        "TwistedFate",
        "Veigar",
        "Vex",
        "Viktor",
        "Vladimir",
        "Xerath",
        "Yasuo",
        "Yone",
        "Zed",
        "Ziggs",
        "Zoe",
    ],
    "BOTTOM": [
        "Aphelios",
        "Ashe",
        "Caitlyn",
        "Draven",
        "Ezreal",
        "Jhin",
        "Jinx",
        "KaiSa",
        "Kalista",
        "KogMaw",
        "Lucian",
        "MissFortune",
        "Nilah",
        "Samira",
        "Senna",
        "Sivir",
        "Smolder",
        "Tristana",
        "Twitch",
        "Varus",
        "Vayne",
        "Xayah",
        "Zeri",
    ],
    "UTILITY": [
        "Alistar",
        "Bard",
        "Blitzcrank",
        "Braum",
        "Janna",
        "Karma",
        "Leona",
        "Lulu",
        "Lux",
        "Milio",
        "Morgana",
        "Nami",
        "Nautilus",
        "Pyke",
        "Rakan",
        "Rell",
        "Renata",
        "Senna",
        "Seraphine",
        "Sona",
        "Soraka",
        "TahmKench",
        "Taric",
        "Thresh",
        "Yuumi",
        "Zilean",
        "Zyra",
    ],
}


class DraftAnalysisRequest(BaseModel):
    players: list[dict]  # [{riot_id: "Name#Tag", role: "TOP"}, ...]
    banned_champions: list[str] = []
    picked_champions: list[str] = []
    enemy_champions: list[str] = []


@app.post("/draft/analyze")
async def analyze_draft(request: DraftAnalysisRequest):
    """Analyse un draft et recommande des champions basés sur les masteries des joueurs"""

    recommendations = []

    for player in request.players:
        riot_id = player.get("riot_id", "")
        role = player.get("role", "").upper()

        if not riot_id or not role or role not in ROLES:
            continue

        # Récupérer les masteries du joueur
        player_masteries = []
        if "#" in riot_id:
            game_name, tag_line = riot_id.rsplit("#", 1)
            puuid = get_puuid_from_riot_id(game_name, tag_line)
            if puuid:
                raw_masteries = fetch_masteries_from_riot(puuid)
                time.sleep(0.5)  # Rate limiting
                for m in raw_masteries:
                    champ_id = m.get("championId")
                    champ_name = CHAMPION_NAMES.get(champ_id, "")
                    if champ_name:
                        player_masteries.append(
                            {
                                "name": champ_name,
                                "level": m.get("championLevel", 0),
                                "points": m.get("championPoints", 0),
                            }
                        )

        # Champions jouables pour ce rôle
        role_champions = set(CHAMPIONS_BY_ROLE.get(role, []))

        # Exclure les bans et les picks déjà pris
        excluded = set(
            request.banned_champions + request.picked_champions + request.enemy_champions
        )
        available_champions = role_champions - excluded

        # Filtrer et scorer les champions basés sur les masteries
        scored_champions = []
        mastery_dict = {m["name"]: m for m in player_masteries}

        for champ in available_champions:
            mastery = mastery_dict.get(champ)
            if mastery:
                # Score basé sur niveau de maîtrise et points
                score = mastery["level"] * 10000 + mastery["points"]
                scored_champions.append(
                    {
                        "champion": champ,
                        "mastery_level": mastery["level"],
                        "mastery_points": mastery["points"],
                        "score": score,
                        "playable": True,
                    }
                )
            else:
                # Champion disponible mais pas joué par le joueur
                scored_champions.append(
                    {
                        "champion": champ,
                        "mastery_level": 0,
                        "mastery_points": 0,
                        "score": 0,
                        "playable": False,
                    }
                )

        # Trier par score décroissant
        scored_champions.sort(key=lambda x: x["score"], reverse=True)

        # Garder seulement les champions que le joueur joue (mastery > 0) ou top 5 si aucun
        playable = [c for c in scored_champions if c["playable"]]
        if not playable:
            playable = scored_champions[:5]

        recommendations.append(
            {
                "riot_id": riot_id,
                "role": role,
                "recommended_champions": playable[:10],  # Top 10 recommendations
                "total_masteries_found": len(player_masteries),
            }
        )

    return {
        "recommendations": recommendations,
        "banned": request.banned_champions,
        "picked": request.picked_champions,
        "enemy": request.enemy_champions,
    }


# ============================================
# Recommandations basées sur Méta + Masteries + Counters
# ============================================


@app.get("/recommend/{riot_id}")
async def recommend_champions(
    riot_id: str,
    role: Optional[str] = None,
    top_n: int = 5,
    min_pickrate: float = 1.0,
    mode: str = "balanced",
    enemy_champions: Optional[str] = None,
    ally_champions: Optional[str] = None,
    banned_champions: Optional[str] = None,
):
    """
    Recommande des champions basés sur la méta, les masteries ET le contexte du draft

    - riot_id: Riot ID du joueur (ex: "Player#EUW")
    - role: Rôle spécifique (top, jng, mid, bot, sup) ou tous si non spécifié
    - top_n: Nombre de recommandations par rôle
    - min_pickrate: Pickrate minimum en % pour être recommandé (défaut: 1%)
    - mode: Mode de recommandation
        - "balanced": Équilibre méta + masteries + counters
        - "counter": Priorité aux counter-picks (quand enemy_champions fourni)
        - "blind": Priorité aux picks safe (peu de counters)
        - "comfort": Priorité aux masteries du joueur
    - enemy_champions: Champions ennemis séparés par virgule (ex: "Yone,Jinx,Thresh")
    - ally_champions: Champions alliés séparés par virgule
    - banned_champions: Champions bannis séparés par virgule
    """
    riot_id = unquote(riot_id)

    # Parser les listes de champions
    enemy_list = [c.strip() for c in enemy_champions.split(",")] if enemy_champions else None
    ally_list = [c.strip() for c in ally_champions.split(",")] if ally_champions else None
    banned_list = [c.strip() for c in banned_champions.split(",")] if banned_champions else None

    # Charger les masteries du joueur
    masteries_data = load_json(MASTERIES_FILE)

    if riot_id not in masteries_data:
        raise HTTPException(
            status_code=404, detail="Masteries non trouvées. Connectez-vous d'abord."
        )

    player_masteries = masteries_data[riot_id].get("masteries", [])

    if not player_masteries:
        raise HTTPException(status_code=400, detail="Aucune mastery trouvée pour ce joueur")

    # Obtenir les recommandations
    recommendations = get_recommendations(
        masteries=player_masteries,
        role=role,
        top_n=top_n,
        min_pickrate=min_pickrate,
        enemy_champions=enemy_list,
        ally_champions=ally_list,
        banned_champions=banned_list,
        mode=mode,
    )

    # Grouper par rôle
    by_role = {}
    for rec in recommendations:
        r = rec["role"]
        if r not in by_role:
            by_role[r] = []
        by_role[r].append(rec)

    return {
        "riot_id": riot_id,
        "role_filter": role,
        "mode": mode,
        "enemy_champions": enemy_list,
        "recommendations": by_role,
        "total_masteries": len(player_masteries),
    }


@app.post("/players/add/{game_name}/{tag_line}")
async def add_player(game_name: str, tag_line: str):
    """
    Ajoute un joueur à la base de données (sans mot de passe, juste pour les masteries)
    Utile pour tracker les masteries des joueurs de l'équipe
    """
    riot_id = f"{game_name}#{tag_line}"

    # Vérifier si déjà dans la base
    masteries_data = load_json(MASTERIES_FILE)
    if riot_id in masteries_data:
        # Rafraîchir les masteries
        puuid = masteries_data[riot_id].get("puuid")
        if puuid:
            await update_user_masteries(riot_id, puuid)
            return {"message": "Masteries rafraîchies", "riot_id": riot_id}
        return {"message": "Joueur déjà enregistré", "riot_id": riot_id}

    # Récupérer le PUUID
    puuid = get_puuid_from_riot_id(game_name, tag_line)
    if not puuid:
        raise HTTPException(status_code=404, detail="Joueur non trouvé sur le serveur Riot")

    # Sauvegarder les masteries
    raw_masteries = fetch_masteries_from_riot(puuid)

    masteries = []
    for m in raw_masteries:
        champion_id = m.get("championId")
        masteries.append(
            {
                "champion_id": champion_id,
                "champion_name": CHAMPION_NAMES.get(champion_id, f"Champion_{champion_id}"),
                "champion_level": m.get("championLevel", 0),
                "champion_points": m.get("championPoints", 0),
                "last_play_time": m.get("lastPlayTime"),
            }
        )

    masteries_data[riot_id] = {
        "puuid": puuid,
        "masteries": masteries,
        "updated_at": int(time.time()),
    }
    save_json(MASTERIES_FILE, masteries_data)

    return {
        "message": "Joueur ajouté avec succès",
        "riot_id": riot_id,
        "puuid": puuid,
        "masteries_count": len(masteries),
    }


@app.get("/players")
async def list_players():
    """Liste tous les joueurs enregistrés"""
    masteries_data = load_json(MASTERIES_FILE)

    players = []
    for riot_id, data in masteries_data.items():
        players.append(
            {
                "riot_id": riot_id,
                "masteries_count": len(data.get("masteries", [])),
                "updated_at": data.get("updated_at"),
            }
        )

    return {"players": players, "total": len(players)}


@app.get("/meta/tierlist")
async def meta_tierlist(role: Optional[str] = None):
    """
    Retourne la tierlist de la méta actuelle

    - role: Filtrer par rôle (top, jng, mid, bot, sup)
    """
    tierlist = get_meta_tierlist(role=role)

    if not tierlist:
        raise HTTPException(status_code=503, detail="Dataset non disponible")

    return {"role_filter": role, "tierlist": tierlist}


@app.get("/meta/champion/{champion}")
async def meta_champion_stats(champion: str, role: str = "mid"):
    """
    Retourne les stats d'un champion depuis Lolalytics
    """
    from api.lolalytics_scraper import get_champion_stats

    stats = get_champion_stats(champion, role)

    if not stats or stats.get("games", 0) == 0:
        raise HTTPException(
            status_code=404, detail=f"Champion '{champion}' non trouvé dans la méta"
        )

    return {"champion": champion, "role": role, "stats": stats}


# ============================================
# Lolalytics Stats - Matchups et Counters
# ============================================


@app.get("/lolalytics/{champion}/{role}")
async def lolalytics_champion_stats(champion: str, role: str):
    """
    Récupère les stats d'un champion depuis Lolalytics

    - champion: Nom du champion (ex: "Yone", "LeeSin")
    - role: Rôle (top, jng, mid, bot, sup)

    Returns:
        - counters: Champions contre lesquels on est fort (WR >= 52%)
        - weak_against: Champions contre lesquels on est faible (WR <= 48%)
        - winrate: Winrate global du champion
        - games: Nombre de games analysées
    """
    try:
        stats = get_champion_stats(champion, role)

        if not stats or stats.get("games", 0) == 0:
            raise HTTPException(status_code=404, detail=f"Pas de données pour {champion} {role}")

        return {"champion": champion, "role": role, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Match History - Historique des parties
# ============================================


def get_match_ids(puuid: str, count: int = 20) -> list:
    """Récupère les IDs des dernières parties ranked d'un joueur"""
    if not RIOT_API_KEY:
        return []

    routing = get_routing(RIOT_REGION)
    # Queue 420 = Ranked Solo/Duo, 440 = Ranked Flex
    url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {
        "queue": 420,  # Ranked Solo/Duo
        "type": "ranked",
        "start": 0,
        "count": count,
    }
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        print(f"Error getting match IDs: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error getting match IDs: {e}")
    return []


def get_match_details(match_id: str) -> Optional[dict]:
    """Récupère les détails d'une partie"""
    if not RIOT_API_KEY:
        return None

    routing = get_routing(RIOT_REGION)
    url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error getting match details: {e}")
    return None


def format_match_for_frontend(match_data: dict, searched_puuid: str) -> dict:
    """Formate les données d'un match pour le frontend"""
    info = match_data.get("info", {})
    participants = info.get("participants", [])

    # Séparer les équipes
    team_100 = []
    team_200 = []
    player_win = False
    team_100_win = False
    player_data_searched = None

    for p in participants:
        player_data = {
            "championId": p.get("championId"),
            "championName": p.get("championName"),
            "teamPosition": p.get("teamPosition", ""),
            "summonerName": p.get("summonerName", ""),
            "riotIdGameName": p.get("riotIdGameName", ""),
            "riotIdTagline": p.get("riotIdTagline", ""),
            "kills": p.get("kills", 0),
            "deaths": p.get("deaths", 0),
            "assists": p.get("assists", 0),
            "cs": p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
            "visionScore": p.get("visionScore", 0),
            "goldEarned": p.get("goldEarned", 0),
            "totalDamageDealt": p.get("totalDamageDealtToChampions", 0),
            "totalDamageTaken": p.get("totalDamageTaken", 0),
            "win": p.get("win", False),
        }

        if p.get("teamId") == 100:
            team_100.append(player_data)
            if p.get("win"):
                team_100_win = True
        else:
            team_200.append(player_data)

        # Vérifier si c'est le joueur recherché
        if p.get("puuid") == searched_puuid:
            player_win = p.get("win", False)
            player_data_searched = player_data

    return {
        "match_id": match_data.get("metadata", {}).get("matchId"),
        "game_duration": info.get("gameDuration", 0),
        "game_mode": info.get("gameMode", ""),
        "game_version": info.get("gameVersion", ""),
        "queue_id": info.get("queueId", 0),
        "game_creation": info.get("gameCreation", 0),
        "team_100_win": team_100_win,
        "team_100_champions": team_100,
        "team_200_champions": team_200,
        "playerWin": player_win,
        "playerData": player_data_searched,
    }


@app.get("/matches/{game_name}/{tag_line}")
async def get_player_matches(game_name: str, tag_line: str, count: int = 20):
    """
    Récupère les dernières parties ranked d'un joueur

    - game_name: Nom du joueur (ex: "KKC Sulfy")
    - tag_line: Tag du joueur (ex: "SuS")
    - count: Nombre de parties (max 20)
    """
    if not RIOT_API_KEY:
        raise HTTPException(status_code=503, detail="API Riot non configurée")

    # Limiter à 20 parties
    count = min(count, 20)

    # Récupérer le PUUID
    puuid = get_puuid_from_riot_id(game_name, tag_line)
    if not puuid:
        raise HTTPException(status_code=404, detail=f"Joueur '{game_name}#{tag_line}' non trouvé")

    # Récupérer les match IDs
    match_ids = get_match_ids(puuid, count)
    if not match_ids:
        raise HTTPException(status_code=404, detail="Aucune partie ranked trouvée")

    # Récupérer les détails de chaque match
    matches = []
    for match_id in match_ids:
        match_data = get_match_details(match_id)
        if match_data:
            formatted = format_match_for_frontend(match_data, puuid)
            matches.append(formatted)

    return {
        "player": f"{game_name}#{tag_line}",
        "puuid": puuid,
        "matches": matches,
        "total": len(matches),
    }
