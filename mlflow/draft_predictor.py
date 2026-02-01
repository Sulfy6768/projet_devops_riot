"""
Draft Prediction - Live Inference
Use trained model to recommend picks/bans during live draft
"""

import torch
import torch.nn as nn
import json
import numpy as np
from typing import List, Dict, Optional, Tuple

# Import model architecture
from draft_model import DraftLSTM, POSITIONS


class DraftPredictor:
    """Live draft prediction and recommendation system"""
    
    def __init__(self, model_path: str, encoders_path: str, device: str = "cpu"):
        self.device = device
        
        # Load encoders
        with open(encoders_path, "r") as f:
            encoders = json.load(f)
        
        self.champion_encoder = encoders["champion_encoder"]
        self.champion_decoder = {int(k): v for k, v in encoders["champion_decoder"].items()}
        self.config = encoders["config"]
        
        # Load model
        self.model = DraftLSTM(
            num_champions=len(self.champion_encoder),
            embedding_dim=self.config["embedding_dim"],
            hidden_dim=self.config["hidden_dim"],
            num_layers=self.config["num_layers"],
            dropout=0  # No dropout for inference
        )
        self.model.load_state_dict(torch.load(model_path, map_location=device))
        self.model.to(device)
        self.model.eval()
        
        # All champions list
        self.all_champions = list(self.champion_encoder.keys())
    
    def encode_draft_state(self, draft_state: Dict) -> Tuple[torch.Tensor, ...]:
        """
        Encode current draft state into model input tensors
        
        draft_state format:
        {
            "blue_bans": ["Champ1", "Champ2", ...],
            "red_bans": ["Champ1", "Champ2", ...],
            "blue_picks": [("Champ", "pos"), ("Champ", "pos"), ...],
            "red_picks": [("Champ", "pos"), ("Champ", "pos"), ...]
        }
        """
        sequence = []
        
        # Blue bans
        for champ in draft_state.get("blue_bans", []):
            if champ:
                champ_id = self.champion_encoder.get(champ, 0)
                sequence.append({
                    "champ_id": champ_id,
                    "pos_id": 5,  # ban
                    "is_ban": 1,
                    "is_blue": 1
                })
        
        # Red bans
        for champ in draft_state.get("red_bans", []):
            if champ:
                champ_id = self.champion_encoder.get(champ, 0)
                sequence.append({
                    "champ_id": champ_id,
                    "pos_id": 5,  # ban
                    "is_ban": 1,
                    "is_blue": 0
                })
        
        # Blue picks
        for pick in draft_state.get("blue_picks", []):
            if pick:
                champ, pos = pick if isinstance(pick, tuple) else (pick, "mid")
                champ_id = self.champion_encoder.get(champ, 0)
                pos_id = POSITIONS.index(pos) if pos in POSITIONS else 0
                sequence.append({
                    "champ_id": champ_id,
                    "pos_id": pos_id,
                    "is_ban": 0,
                    "is_blue": 1
                })
        
        # Red picks
        for pick in draft_state.get("red_picks", []):
            if pick:
                champ, pos = pick if isinstance(pick, tuple) else (pick, "mid")
                champ_id = self.champion_encoder.get(champ, 0)
                pos_id = POSITIONS.index(pos) if pos in POSITIONS else 0
                sequence.append({
                    "champ_id": champ_id,
                    "pos_id": pos_id,
                    "is_ban": 0,
                    "is_blue": 0
                })
        
        # Pad to 20
        max_len = 20
        while len(sequence) < max_len:
            sequence.append({"champ_id": 0, "pos_id": 0, "is_ban": 0, "is_blue": 0})
        
        # Convert to tensors
        champ_ids = torch.tensor([[s["champ_id"] for s in sequence[:max_len]]], dtype=torch.long)
        pos_ids = torch.tensor([[s["pos_id"] for s in sequence[:max_len]]], dtype=torch.long)
        is_ban = torch.tensor([[s["is_ban"] for s in sequence[:max_len]]], dtype=torch.float)
        is_blue = torch.tensor([[s["is_blue"] for s in sequence[:max_len]]], dtype=torch.float)
        
        return champ_ids.to(self.device), pos_ids.to(self.device), \
               is_ban.to(self.device), is_blue.to(self.device)
    
    def predict_win_probability(self, draft_state: Dict) -> Dict[str, float]:
        """Predict win probability for both teams given current draft"""
        champ_ids, pos_ids, is_ban, is_blue = self.encode_draft_state(draft_state)
        
        with torch.no_grad():
            win_prob, _ = self.model(champ_ids, pos_ids, is_ban, is_blue)
            blue_win_prob = win_prob.item()
        
        return {
            "blue_win_probability": round(blue_win_prob * 100, 2),
            "red_win_probability": round((1 - blue_win_prob) * 100, 2)
        }
    
    def get_unavailable_champions(self, draft_state: Dict) -> set:
        """Get set of champions that are already picked or banned"""
        unavailable = set()
        
        for champ in draft_state.get("blue_bans", []):
            if champ:
                unavailable.add(champ)
        for champ in draft_state.get("red_bans", []):
            if champ:
                unavailable.add(champ)
        for pick in draft_state.get("blue_picks", []):
            if pick:
                champ = pick[0] if isinstance(pick, tuple) else pick
                unavailable.add(champ)
        for pick in draft_state.get("red_picks", []):
            if pick:
                champ = pick[0] if isinstance(pick, tuple) else pick
                unavailable.add(champ)
        
        return unavailable
    
    def recommend_pick(self, draft_state: Dict, team: str, position: str, 
                       top_k: int = 5) -> List[Dict]:
        """
        Recommend best champions to pick for a team/position
        
        Returns list of {champion, score, win_probability_delta}
        """
        unavailable = self.get_unavailable_champions(draft_state)
        available = [c for c in self.all_champions if c not in unavailable]
        
        # Get current win probability
        current_probs = self.predict_win_probability(draft_state)
        
        recommendations = []
        pick_key = "blue_picks" if team == "blue" else "red_picks"
        
        for champ in available:
            # Create hypothetical draft with this pick
            test_state = {
                "blue_bans": draft_state.get("blue_bans", []).copy(),
                "red_bans": draft_state.get("red_bans", []).copy(),
                "blue_picks": [p for p in draft_state.get("blue_picks", [])],
                "red_picks": [p for p in draft_state.get("red_picks", [])]
            }
            test_state[pick_key] = test_state[pick_key] + [(champ, position)]
            
            # Get new win probability
            new_probs = self.predict_win_probability(test_state)
            
            # Calculate delta (positive = good for picking team)
            if team == "blue":
                delta = new_probs["blue_win_probability"] - current_probs["blue_win_probability"]
            else:
                delta = new_probs["red_win_probability"] - current_probs["red_win_probability"]
            
            recommendations.append({
                "champion": champ,
                "position": position,
                "score": delta,
                "new_win_probability": new_probs[f"{team}_win_probability"]
            })
        
        # Sort by score (highest first)
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return recommendations[:top_k]
    
    def recommend_ban(self, draft_state: Dict, team: str, top_k: int = 5) -> List[Dict]:
        """
        Recommend best champions to ban for a team
        
        Bans the champions that would help the opponent the most
        """
        unavailable = self.get_unavailable_champions(draft_state)
        available = [c for c in self.all_champions if c not in unavailable]
        
        opponent = "red" if team == "blue" else "blue"
        
        recommendations = []
        
        for champ in available:
            # Test how much this champion would help the opponent if they picked it
            max_delta = 0
            
            for pos in POSITIONS:
                test_state = {
                    "blue_bans": draft_state.get("blue_bans", []).copy(),
                    "red_bans": draft_state.get("red_bans", []).copy(),
                    "blue_picks": [p for p in draft_state.get("blue_picks", [])],
                    "red_picks": [p for p in draft_state.get("red_picks", [])]
                }
                
                pick_key = f"{opponent}_picks"
                test_state[pick_key] = test_state[pick_key] + [(champ, pos)]
                
                new_probs = self.predict_win_probability(test_state)
                delta = new_probs[f"{opponent}_win_probability"]
                
                if delta > max_delta:
                    max_delta = delta
            
            recommendations.append({
                "champion": champ,
                "opponent_win_boost": max_delta,
                "ban_value": max_delta  # Higher = more valuable to ban
            })
        
        # Sort by ban value (highest first = most impactful to ban)
        recommendations.sort(key=lambda x: x["ban_value"], reverse=True)
        
        return recommendations[:top_k]


# ============================================
# Example Usage
# ============================================
def demo():
    """Demo the predictor"""
    print("Loading model...")
    predictor = DraftPredictor(
        model_path="mlflow/best_draft_model.pth",
        encoders_path="mlflow/draft_encoders.json"
    )
    
    # Example draft state (mid-draft)
    draft_state = {
        "blue_bans": ["Yone", "Aurora", "Corki"],
        "red_bans": ["Ksante", "Rumble", "Viego"],
        "blue_picks": [("Jinx", "bot")],
        "red_picks": [("Nautilus", "sup"), ("Graves", "jng")]
    }
    
    print("\n" + "="*50)
    print("Current Draft State:")
    print(f"  Blue bans: {draft_state['blue_bans']}")
    print(f"  Red bans: {draft_state['red_bans']}")
    print(f"  Blue picks: {draft_state['blue_picks']}")
    print(f"  Red picks: {draft_state['red_picks']}")
    
    # Win probability
    probs = predictor.predict_win_probability(draft_state)
    print(f"\nWin Probabilities:")
    print(f"  Blue: {probs['blue_win_probability']}%")
    print(f"  Red: {probs['red_win_probability']}%")
    
    # Recommend pick for Blue team mid
    print(f"\nRecommended picks for Blue (mid):")
    picks = predictor.recommend_pick(draft_state, "blue", "mid", top_k=5)
    for i, rec in enumerate(picks, 1):
        print(f"  {i}. {rec['champion']} (+{rec['score']:.2f}% win rate)")
    
    # Recommend ban for Blue team
    print(f"\nRecommended bans for Blue:")
    bans = predictor.recommend_ban(draft_state, "blue", top_k=5)
    for i, rec in enumerate(bans, 1):
        print(f"  {i}. {rec['champion']} (opponent +{rec['ban_value']:.2f}% if picked)")


if __name__ == "__main__":
    demo()
