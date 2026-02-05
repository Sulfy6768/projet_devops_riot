"""
Lolalytics Scraper - Récupère les données de matchups/counters depuis Lolalytics
"""
import httpx
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Cache pour éviter de spam Lolalytics
CACHE_FILE = Path("/app/data/lolalytics_cache.json")
CACHE_DURATION = timedelta(hours=6)  # Refresh toutes les 6h

# Mapping des rôles pour Lolalytics
ROLE_MAP = {
    "top": "top",
    "jng": "jungle",
    "jungle": "jungle",
    "mid": "middle",
    "middle": "middle",
    "bot": "bottom",
    "adc": "bottom",
    "bottom": "bottom",
    "sup": "support",
    "support": "support"
}


class LolalyticsScraper:
    """Scraper pour récupérer les données de Lolalytics"""
    
    # API endpoint de Lolalytics (a1.lolalytics.com fonctionne)
    BASE_URL = "https://a1.lolalytics.com/mega/"
    DDRAGON_URL = "https://ddragon.leagueoflegends.com/cdn/14.24.1/data/en_US/champion.json"
    
    def __init__(self):
        self.cache: Dict = {}
        self.cache_time: Optional[datetime] = None
        self.champion_id_to_name: Dict[int, str] = {}
        self.champion_name_to_id: Dict[str, int] = {}
        self._load_champion_mapping()
        self._load_cache()
    
    def _load_champion_mapping(self):
        """Charge le mapping champion ID <-> nom depuis Data Dragon"""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.DDRAGON_URL)
                if response.status_code == 200:
                    data = response.json()
                    champions = data.get("data", {})
                    for name, info in champions.items():
                        cid = int(info["key"])
                        self.champion_id_to_name[cid] = name
                        self.champion_name_to_id[name.lower()] = cid
                    print(f"Champion mapping loaded: {len(self.champion_id_to_name)} champions")
        except Exception as e:
            print(f"Error loading champion mapping: {e}")
    
    def _load_cache(self):
        """Charge le cache depuis le fichier"""
        try:
            if CACHE_FILE.exists():
                data = json.loads(CACHE_FILE.read_text(encoding='utf-8'))
                self.cache = data.get("matchups", {})
                cache_time_str = data.get("timestamp")
                if cache_time_str:
                    self.cache_time = datetime.fromisoformat(cache_time_str)
                print(f"Cache Lolalytics chargé: {len(self.cache)} champions")
        except Exception as e:
            print(f"Erreur chargement cache Lolalytics: {e}")
            self.cache = {}
    
    def _save_cache(self):
        """Sauvegarde le cache dans le fichier"""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "timestamp": datetime.now().isoformat(),
                "matchups": self.cache
            }
            CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            print(f"Erreur sauvegarde cache Lolalytics: {e}")
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Vérifie si le cache est encore valide pour un champion"""
        if cache_key not in self.cache:
            return False
        if not self.cache_time:
            return False
        return datetime.now() - self.cache_time < CACHE_DURATION
    
    def fetch_champion_data(self, champion: str, role: str) -> Dict:
        """
        Récupère les données d'un champion depuis Lolalytics (synchrone)
        
        Returns:
            {
                "counters": [{"champion": "Darius", "winrate": 45.2, "games": 1500}, ...],
                "weak_against": [{"champion": "Teemo", "winrate": 55.3, "games": 1200}, ...],
                "winrate": 51.5,
                "games": 50000
            }
        """
        lola_role = ROLE_MAP.get(role.lower(), role.lower())
        cache_key = f"{champion.lower()}_{lola_role}"
        
        # Vérifier le cache
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            # Normaliser le nom du champion pour l'API
            champ_name = champion.replace(" ", "").replace("'", "").lower()
            
            # URL de l'API Lolalytics - endpoint counter
            params = {
                "ep": "counter",
                "p": "d",
                "v": "1",
                "patch": "14",
                "c": champ_name,
                "lane": lola_role,
                "tier": "emerald_plus",
                "queue": "420",
                "region": "all"
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://lolalytics.com/",
                "Origin": "https://lolalytics.com"
            }
            
            print(f"Fetching Lolalytics data for {champion} {role}...")
            
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                response = client.get(self.BASE_URL, params=params, headers=headers)
                
                if response.status_code != 200:
                    print(f"Lolalytics API error {response.status_code} for {champion} {role}")
                    return self._get_empty_data()
                
                data = response.json()
                result = self._parse_counter_data(data, champion)
                
                # Sauvegarder dans le cache
                self.cache[cache_key] = result
                self.cache_time = datetime.now()
                self._save_cache()
                
                print(f"Got {len(result.get('counters', []))} counters, {len(result.get('weak_against', []))} weak matchups for {champion}")
                return result
                
        except Exception as e:
            print(f"Erreur fetch Lolalytics pour {champion} {role}: {e}")
            return self._get_empty_data()
    
    def _parse_counter_data(self, data: Dict, champion: str) -> Dict:
        """Parse les données de l'endpoint counter de Lolalytics"""
        result = {
            "counters": [],       # Champions que ce champion counter (winrate élevé contre eux)
            "weak_against": [],   # Champions qui counter ce champion (winrate faible contre eux)
            "winrate": 50.0,
            "pickrate": 0.0,      # Pickrate sur cette lane
            "banrate": 0.0,
            "games": 0
        }
        
        try:
            # Stats globales du champion
            stats = data.get("stats", {})
            if stats:
                result["winrate"] = float(stats.get("wr", 50.0))
                result["pickrate"] = float(stats.get("pr", 0.0))  # Pickrate en %
                result["banrate"] = float(stats.get("br", 0.0))
                # "analysed" est le nombre total de games analysées
                result["games"] = stats.get("analysed", 0)
            
            # Matchups contre d'autres champions
            # Dans "counters", vsWr est le winrate DU champion analysé contre cet ennemi
            # vsWr > 50 = on gagne contre eux = ils sont weak against nous
            # vsWr < 50 = on perd contre eux = ils nous counter
            counters_list = data.get("counters", [])
            
            for matchup in counters_list:
                if not isinstance(matchup, dict):
                    continue
                
                cid = matchup.get("cid")
                games = matchup.get("n", 0)
                vs_wr = matchup.get("vsWr", 50.0)  # Notre winrate contre eux
                
                if games < 100:  # Minimum de games pour être significatif
                    continue
                
                # Récupérer le nom du champion
                champ_name = self.champion_id_to_name.get(cid, f"Champion_{cid}")
                
                matchup_data = {
                    "champion": champ_name,
                    "winrate": round(vs_wr, 2),
                    "games": games
                }
                
                # vsWr >= 52 = on gagne souvent = ils sont dans "weak_against" nous
                # vsWr <= 48 = on perd souvent = ils nous "counter"
                if vs_wr >= 52:
                    result["weak_against"].append(matchup_data)  # On gagne contre eux
                elif vs_wr <= 48:
                    result["counters"].append(matchup_data)      # Ils nous counter
            
            # Trier par winrate
            result["counters"].sort(key=lambda x: x["winrate"])  # Les plus bas en premier (nos pires matchups)
            result["weak_against"].sort(key=lambda x: x["winrate"], reverse=True)  # Les plus hauts en premier
            
            # Limiter à 15
            result["counters"] = result["counters"][:15]
            result["weak_against"] = result["weak_against"][:15]
            
        except Exception as e:
            print(f"Erreur parsing Lolalytics counter data: {e}")
        
        return result
    
    def _get_empty_data(self) -> Dict:
        """Retourne des données vides"""
        return {
            "counters": [],
            "weak_against": [],
            "winrate": 50.0,
            "pickrate": 0.0,
            "banrate": 0.0,
            "games": 0
        }
    
    def get_counter_score(self, champion: str, role: str, enemy_champions: List[str]) -> float:
        """
        Calcule un score de counter pour un champion contre une équipe adverse
        
        Returns:
            Score entre 0 et 100 (100 = excellent counter)
        """
        if not enemy_champions:
            return 50.0
        
        data = self.fetch_champion_data(champion, role)
        
        if not data or data.get("games", 0) == 0:
            return 50.0
        
        counters_dict = {m["champion"].lower(): m["winrate"] for m in data.get("counters", [])}
        weak_dict = {m["champion"].lower(): m["winrate"] for m in data.get("weak_against", [])}
        
        total_score = 0
        matched = 0
        
        for enemy in enemy_champions:
            enemy_lower = enemy.lower()
            
            if enemy_lower in counters_dict:
                total_score += counters_dict[enemy_lower]
                matched += 1
            elif enemy_lower in weak_dict:
                total_score += weak_dict[enemy_lower]
                matched += 1
            else:
                total_score += 50
                matched += 1
        
        if matched == 0:
            return 50.0
        
        avg_winrate = total_score / matched
        score = (avg_winrate - 45) * 10
        return max(0, min(100, score))
    
    def get_blindpick_score(self, champion: str, role: str) -> float:
        """
        Calcule un score de blind pick (sécurité du pick)
        
        Returns:
            Score entre 0 et 100 (100 = très safe en blind)
        """
        data = self.fetch_champion_data(champion, role)
        
        if not data or data.get("games", 0) == 0:
            return 50.0
        
        weak_against = data.get("weak_against", [])
        
        if not weak_against:
            return 75.0
        
        hard_counters = len([m for m in weak_against if m["winrate"] < 45])
        soft_counters = len([m for m in weak_against if 45 <= m["winrate"] < 48])
        
        penalty = hard_counters * 12 + soft_counters * 4
        
        global_wr = data.get("winrate", 50)
        bonus = max(0, (global_wr - 50) * 2)
        
        score = 70 - penalty + bonus
        return max(0, min(100, score))


# Instance globale
scraper = LolalyticsScraper()


def get_counter_score(champion: str, role: str, enemy_champions: List[str]) -> float:
    """Fonction helper pour le score de counter"""
    return scraper.get_counter_score(champion, role, enemy_champions)


def get_blindpick_score(champion: str, role: str) -> float:
    """Fonction helper pour le score de blind pick"""
    return scraper.get_blindpick_score(champion, role)


def get_champion_stats(champion: str, role: str) -> Dict:
    """Fonction helper pour les stats d'un champion"""
    return scraper.fetch_champion_data(champion, role)
