"""
Draft Prediction Model - League of Legends
LSTM model to predict win probability and recommend picks/bans during live draft

Architecture:
- Champion embeddings (learned representations)
- Position embeddings (TOP, JGL, MID, BOT, SUP)
- Side embedding (Blue/Red)
- LSTM to process draft sequence
- Output: Win probability + champion scores for next pick/ban
"""

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import mlflow
import mlflow.pytorch
from tqdm import tqdm
import json
import os

# ============================================
# Configuration
# ============================================
CONFIG = {
    "data_path": "Dataset/master_enriched_team.csv",
    "embedding_dim": 64,
    "hidden_dim": 128,
    "num_layers": 2,
    "dropout": 0.3,
    "batch_size": 64,
    "epochs": 50,
    "learning_rate": 0.001,
    "device": "cuda" if torch.cuda.is_available() else "cpu"
}

# Draft sequence order (10 bans then 10 picks)
# Blue: B1, B2, B3 | Red: B4, B5, B6 | Blue: B7, B8 | Red: B9, B10
# Blue: P1 | Red: P2, P3 | Blue: P4, P5 | Red: P6, P7 | Blue: P8, P9 | Red: P10
DRAFT_ORDER = [
    ("blue", "ban", 1), ("blue", "ban", 2), ("blue", "ban", 3),
    ("red", "ban", 1), ("red", "ban", 2), ("red", "ban", 3),
    ("blue", "pick", 1),
    ("red", "pick", 1), ("red", "pick", 2),
    ("blue", "pick", 2), ("blue", "pick", 3),
    ("red", "pick", 3), ("red", "pick", 4),
    ("blue", "ban", 4), ("blue", "ban", 5),
    ("red", "ban", 4), ("red", "ban", 5),
    ("red", "pick", 5),
    ("blue", "pick", 4), ("blue", "pick", 5),
]

POSITIONS = ["top", "jng", "mid", "bot", "sup"]


# ============================================
# Data Preparation
# ============================================
class DraftDataset(Dataset):
    """Dataset for draft sequences"""
    
    def __init__(self, games_data, champion_encoder, max_champions):
        self.games = games_data
        self.champion_encoder = champion_encoder
        self.max_champions = max_champions
    
    def __len__(self):
        return len(self.games)
    
    def __getitem__(self, idx):
        game = self.games[idx]
        
        # Encode draft sequence
        # Format: [champion_id, position_id, is_ban, team_side]
        sequence = []
        
        for side in ["blue", "red"]:
            team = game[side]
            
            # Bans (position = 5 for ban, no position)
            for i in range(1, 6):
                ban_key = f"ban{i}"
                if ban_key in team and pd.notna(team[ban_key]):
                    champ = team[ban_key]
                    champ_id = self.champion_encoder.get(champ, 0)
                    sequence.append({
                        "champ_id": champ_id,
                        "pos_id": 5,  # 5 = ban (no position)
                        "is_ban": 1,
                        "is_blue": 1 if side == "blue" else 0
                    })
            
            # Picks (with position)
            for i in range(1, 6):
                pick_key = f"pick{i}"
                if pick_key in team and pd.notna(team[pick_key]):
                    pick_val = team[pick_key]
                    # Format: "Champion.position" (e.g., "Jinx.bot")
                    if "." in str(pick_val):
                        champ, pos = pick_val.rsplit(".", 1)
                        pos_id = POSITIONS.index(pos) if pos in POSITIONS else 0
                    else:
                        champ = pick_val
                        pos_id = 0
                    
                    champ_id = self.champion_encoder.get(champ, 0)
                    sequence.append({
                        "champ_id": champ_id,
                        "pos_id": pos_id,
                        "is_ban": 0,
                        "is_blue": 1 if side == "blue" else 0
                    })
        
        # Pad sequence to fixed length (20: 10 bans + 10 picks)
        max_len = 20
        while len(sequence) < max_len:
            sequence.append({"champ_id": 0, "pos_id": 0, "is_ban": 0, "is_blue": 0})
        
        # Convert to tensors
        champ_ids = torch.tensor([s["champ_id"] for s in sequence[:max_len]], dtype=torch.long)
        pos_ids = torch.tensor([s["pos_id"] for s in sequence[:max_len]], dtype=torch.long)
        is_ban = torch.tensor([s["is_ban"] for s in sequence[:max_len]], dtype=torch.float)
        is_blue = torch.tensor([s["is_blue"] for s in sequence[:max_len]], dtype=torch.float)
        
        # Target: Blue team wins (1) or loses (0)
        result = torch.tensor(game["blue"]["result"], dtype=torch.float)
        
        return {
            "champ_ids": champ_ids,
            "pos_ids": pos_ids,
            "is_ban": is_ban,
            "is_blue": is_blue,
            "result": result
        }


def load_and_prepare_data(data_path):
    """Load CSV and prepare game-level data"""
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path, low_memory=False)
    
    print(f"Dataset shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()[:20]}...")
    
    # Filter to team rows only (position == 'team')
    if 'position' in df.columns:
        df_teams = df[df['position'] == 'team'].copy()
    else:
        df_teams = df.copy()
    
    print(f"Team rows: {df_teams.shape[0]}")
    
    # Build champion vocabulary from bans and picks
    all_champions = set()
    
    for col in ['ban1', 'ban2', 'ban3', 'ban4', 'ban5']:
        if col in df_teams.columns:
            all_champions.update(df_teams[col].dropna().unique())
    
    for col in ['pick1', 'pick2', 'pick3', 'pick4', 'pick5']:
        if col in df_teams.columns:
            # Extract champion name from "Champion.position" format
            picks = df_teams[col].dropna()
            for pick in picks:
                if "." in str(pick):
                    champ = pick.rsplit(".", 1)[0]
                else:
                    champ = pick
                all_champions.add(champ)
    
    # Create champion encoder (0 = padding/unknown)
    all_champions = sorted([c for c in all_champions if pd.notna(c)])
    champion_encoder = {champ: i + 1 for i, champ in enumerate(all_champions)}
    champion_decoder = {i + 1: champ for i, champ in enumerate(all_champions)}
    
    print(f"Unique champions: {len(all_champions)}")
    
    # Group by game to get both teams
    games = []
    game_ids = df_teams['gameid'].unique()
    
    print(f"Processing {len(game_ids)} games...")
    for game_id in tqdm(game_ids, desc="Building games"):
        game_df = df_teams[df_teams['gameid'] == game_id]
        
        blue_team = game_df[game_df['side'] == 'Blue']
        red_team = game_df[game_df['side'] == 'Red']
        
        if len(blue_team) == 0 or len(red_team) == 0:
            continue
        
        blue_row = blue_team.iloc[0]
        red_row = red_team.iloc[0]
        
        game_data = {
            "game_id": game_id,
            "blue": {
                "ban1": blue_row.get('ban1'),
                "ban2": blue_row.get('ban2'),
                "ban3": blue_row.get('ban3'),
                "ban4": blue_row.get('ban4'),
                "ban5": blue_row.get('ban5'),
                "pick1": blue_row.get('pick1'),
                "pick2": blue_row.get('pick2'),
                "pick3": blue_row.get('pick3'),
                "pick4": blue_row.get('pick4'),
                "pick5": blue_row.get('pick5'),
                "result": int(blue_row.get('result', 0))
            },
            "red": {
                "ban1": red_row.get('ban1'),
                "ban2": red_row.get('ban2'),
                "ban3": red_row.get('ban3'),
                "ban4": red_row.get('ban4'),
                "ban5": red_row.get('ban5'),
                "pick1": red_row.get('pick1'),
                "pick2": red_row.get('pick2'),
                "pick3": red_row.get('pick3'),
                "pick4": red_row.get('pick4'),
                "pick5": red_row.get('pick5'),
                "result": int(red_row.get('result', 0))
            }
        }
        games.append(game_data)
    
    print(f"Valid games: {len(games)}")
    
    return games, champion_encoder, champion_decoder


# ============================================
# Model Architecture
# ============================================
class DraftLSTM(nn.Module):
    """LSTM model for draft prediction"""
    
    def __init__(self, num_champions, embedding_dim, hidden_dim, num_layers, dropout):
        super().__init__()
        
        self.num_champions = num_champions
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        
        # Embeddings
        self.champion_embedding = nn.Embedding(num_champions + 1, embedding_dim, padding_idx=0)
        self.position_embedding = nn.Embedding(6, embedding_dim // 4)  # 5 positions + ban
        
        # Input features: champion_emb + position_emb + is_ban + is_blue
        input_dim = embedding_dim + embedding_dim // 4 + 2
        
        # LSTM
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        # Output heads
        self.win_predictor = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid()
        )
        
        # Champion scorer (for recommendations)
        self.champion_scorer = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_champions + 1)
        )
    
    def forward(self, champ_ids, pos_ids, is_ban, is_blue):
        batch_size = champ_ids.size(0)
        
        # Embeddings
        champ_emb = self.champion_embedding(champ_ids)  # (batch, seq, emb)
        pos_emb = self.position_embedding(pos_ids)  # (batch, seq, emb/4)
        
        # Concat all features
        is_ban = is_ban.unsqueeze(-1)  # (batch, seq, 1)
        is_blue = is_blue.unsqueeze(-1)  # (batch, seq, 1)
        
        x = torch.cat([champ_emb, pos_emb, is_ban, is_blue], dim=-1)
        
        # LSTM
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Use last hidden state (concat forward and backward)
        final_hidden = torch.cat([hidden[-2], hidden[-1]], dim=-1)
        
        # Predictions
        win_prob = self.win_predictor(final_hidden).squeeze(-1)
        champ_scores = self.champion_scorer(final_hidden)
        
        return win_prob, champ_scores
    
    def predict_next_pick(self, current_draft, champion_encoder, champion_decoder, 
                          available_champions, side, is_ban=False, top_k=5):
        """Predict best champions for next pick/ban"""
        self.eval()
        device = next(self.parameters()).device
        
        with torch.no_grad():
            # Encode current draft state
            # ... (implementation for live prediction)
            pass
        
        return []


# ============================================
# Training
# ============================================
def train_model(model, train_loader, val_loader, config, device):
    """Train the model with MLflow tracking"""
    
    model = model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    criterion = nn.BCELoss()
    
    best_val_acc = 0
    patience = 10
    patience_counter = 0
    
    for epoch in range(config["epochs"]):
        # Training
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        
        for batch in tqdm(train_loader, desc=f"Epoch {epoch+1}/{config['epochs']}"):
            champ_ids = batch["champ_ids"].to(device)
            pos_ids = batch["pos_ids"].to(device)
            is_ban = batch["is_ban"].to(device)
            is_blue = batch["is_blue"].to(device)
            result = batch["result"].to(device)
            
            optimizer.zero_grad()
            win_prob, _ = model(champ_ids, pos_ids, is_ban, is_blue)
            
            loss = criterion(win_prob, result)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            predictions = (win_prob > 0.5).float()
            train_correct += (predictions == result).sum().item()
            train_total += result.size(0)
        
        train_acc = train_correct / train_total
        avg_train_loss = train_loss / len(train_loader)
        
        # Validation
        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for batch in val_loader:
                champ_ids = batch["champ_ids"].to(device)
                pos_ids = batch["pos_ids"].to(device)
                is_ban = batch["is_ban"].to(device)
                is_blue = batch["is_blue"].to(device)
                result = batch["result"].to(device)
                
                win_prob, _ = model(champ_ids, pos_ids, is_ban, is_blue)
                loss = criterion(win_prob, result)
                
                val_loss += loss.item()
                predictions = (win_prob > 0.5).float()
                val_correct += (predictions == result).sum().item()
                val_total += result.size(0)
        
        val_acc = val_correct / val_total
        avg_val_loss = val_loss / len(val_loader)
        
        # Log metrics
        mlflow.log_metrics({
            "train_loss": avg_train_loss,
            "train_accuracy": train_acc,
            "val_loss": avg_val_loss,
            "val_accuracy": val_acc
        }, step=epoch)
        
        print(f"Epoch {epoch+1}: Train Loss={avg_train_loss:.4f}, Train Acc={train_acc:.4f}, "
              f"Val Loss={avg_val_loss:.4f}, Val Acc={val_acc:.4f}")
        
        # Early stopping
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            patience_counter = 0
            # Save best model
            torch.save(model.state_dict(), "best_draft_model.pth")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
    
    return best_val_acc


# ============================================
# Main
# ============================================
def main():
    print("=" * 60)
    print("Draft Prediction Model - Training")
    print("=" * 60)
    print(f"Device: {CONFIG['device']}")
    
    # Load data
    games, champion_encoder, champion_decoder = load_and_prepare_data(CONFIG["data_path"])
    
    if len(games) == 0:
        print("ERROR: No valid games found!")
        return
    
    # Split data
    train_games, val_games = train_test_split(games, test_size=0.2, random_state=42)
    print(f"Train games: {len(train_games)}, Val games: {len(val_games)}")
    
    # Create datasets
    num_champions = len(champion_encoder)
    train_dataset = DraftDataset(train_games, champion_encoder, num_champions)
    val_dataset = DraftDataset(val_games, champion_encoder, num_champions)
    
    train_loader = DataLoader(train_dataset, batch_size=CONFIG["batch_size"], shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=CONFIG["batch_size"])
    
    # Create model
    model = DraftLSTM(
        num_champions=num_champions,
        embedding_dim=CONFIG["embedding_dim"],
        hidden_dim=CONFIG["hidden_dim"],
        num_layers=CONFIG["num_layers"],
        dropout=CONFIG["dropout"]
    )
    
    print(f"\nModel parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # MLflow tracking
    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment("draft-prediction")
    
    with mlflow.start_run(run_name="lstm-v1"):
        # Log parameters
        mlflow.log_params(CONFIG)
        mlflow.log_param("num_champions", num_champions)
        mlflow.log_param("num_train_games", len(train_games))
        mlflow.log_param("num_val_games", len(val_games))
        
        # Train
        best_acc = train_model(model, train_loader, val_loader, CONFIG, CONFIG["device"])
        
        # Log final metric
        mlflow.log_metric("best_val_accuracy", best_acc)
        
        # Save model and encoders
        model.load_state_dict(torch.load("best_draft_model.pth", weights_only=True))
        
        # Save encoders for inference
        encoders = {
            "champion_encoder": champion_encoder,
            "champion_decoder": champion_decoder,
            "config": CONFIG
        }
        with open("draft_encoders.json", "w") as f:
            json.dump(encoders, f, indent=2)
        
        # Log artifacts to MLflow (automatically stored in artifacts/)
        mlflow.log_artifact("best_draft_model.pth")
        mlflow.log_artifact("draft_encoders.json")
        
        # Log model
        mlflow.pytorch.log_model(model, "draft_model")
        
        print(f"\n✅ Training complete! Best validation accuracy: {best_acc:.4f}")
        print(f"Model saved to MLflow run: {mlflow.active_run().info.run_id}")


if __name__ == "__main__":
    main()
