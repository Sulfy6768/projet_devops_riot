import requests
import time
import json

class RiotAPI:
    def __init__(self, api_key: str, region: str = "euw1"):
        self.api_key = api_key
        self.region = region
        self.routing = self._get_routing(region)
        self.headers = {"X-Riot-Token": api_key}
    
    def _get_routing(self, region: str) -> str:
        """Retourne le routing régional pour les endpoints match-v5"""
        routing_map = {
            "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
            "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
            "kr": "asia", "jp1": "asia",
            "oc1": "sea", "ph2": "sea", "sg2": "sea", "th2": "sea", "tw2": "sea", "vn2": "sea"
        }
        return routing_map.get(region, "europe")
    
    def get_summoner_by_name(self, game_name: str, tag_line: str) -> dict:
        """Récupère le PUUID d'un joueur via Riot ID (GameName#TagLine)"""
        url = f"https://{self.routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_match_ids(self, puuid: str, count: int = 20, queue: int = None, match_type: str = None) -> list:
        """
        Récupère les IDs des dernières parties d'un joueur
        queue: 420 = Ranked Solo/Duo, 440 = Ranked Flex
        match_type: ranked, normal, tourney, tutorial
        """
        url = f"https://{self.routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"count": count}
        if queue:
            params["queue"] = queue
        if match_type:
            params["type"] = match_type
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_match_details(self, match_id: str) -> dict:
        """Récupère les détails complets d'une partie (champions, draft, stats...)"""
        url = f"https://{self.routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def extract_draft_data(self, match_data: dict) -> dict:
        """Extrait les données de draft importantes pour ton IA"""
        info = match_data["info"]
        
        # Équipes et leurs champions
        team_100 = []  # Blue side
        team_200 = []  # Red side
        
        for participant in info["participants"]:
            player_data = {
                "championId": participant["championId"],
                "championName": participant["championName"],
                "teamPosition": participant["teamPosition"],  # TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY
                "win": participant["win"]
            }
            
            if participant["teamId"] == 100:
                team_100.append(player_data)
            else:
                team_200.append(player_data)
        
        # Bans
        bans = {"team_100": [], "team_200": []}
        for team in info["teams"]:
            team_key = f"team_{team['teamId']}"
            bans[team_key] = [ban["championId"] for ban in team["bans"]]
        
        return {
            "match_id": match_data["metadata"]["matchId"],
            "game_version": info["gameVersion"],
            "queue_id": info["queueId"],
            "game_duration": info["gameDuration"],
            "team_100_win": info["teams"][0]["win"],
            "team_100_champions": team_100,
            "team_200_champions": team_200,
            "bans": bans
        }


def collect_games(api: RiotAPI, players: list, games_per_player: int = 100) -> list:
    """
    Collecte des parties depuis une liste de joueurs
    players: liste de tuples (game_name, tag_line)
    """
    all_drafts = []
    seen_matches = set()
    
    for game_name, tag_line in players:
        print(f"Fetching games for {game_name}#{tag_line}...")
        try:
            account = api.get_summoner_by_name(game_name, tag_line)
            puuid = account["puuid"]
            
            match_ids = api.get_match_ids(puuid, count=games_per_player, queue=420)  # Ranked Solo
            
            for match_id in match_ids:
                if match_id in seen_matches:
                    continue
                seen_matches.add(match_id)
                
                try:
                    match_data = api.get_match_details(match_id)
                    draft_data = api.extract_draft_data(match_data)
                    all_drafts.append(draft_data)
                    print(f"  Collected {match_id}")
                except Exception as e:
                    print(f"  Error fetching {match_id}: {e}")
                
                time.sleep(1.2)  # pas plus sinon l'api block c genre 100 truc pas minute
                
        except Exception as e:
            print(f"Error with player {game_name}#{tag_line}: {e}")
    
    return all_drafts


if __name__ == "__main__":
    API_KEY = "RGAPI-243c484b-624d-436d-9dd3-28f208284ff0"
    
    api = RiotAPI(API_KEY, region="euw1")
    
    players = [
        ("KKC Sulfy", "SuS"),
    ]
    
    # Collecte des games
    drafts = collect_games(api, players, games_per_player=50)
    
    # Sauvegarde en JSON
    with open("drafts_data.json", "w") as f:
        json.dump(drafts, f, indent=2)
    
    print(f"\n✅ {len(drafts)} parties collectées et sauvegardées!")
