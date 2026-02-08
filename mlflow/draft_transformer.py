"""
Draft Transformer - Modèle Simplifié (Picks Only)
==================================================

Modèle simplifié qui prédit le gagnant basé uniquement sur :
- Les 5 picks de chaque équipe (avec leur position/rôle)
- Le side (Blue/Red)

Plus de bans, plus d'ordre de draft.

Séquence d'entrée (11 tokens) :
[CLS] [PICK_B1] [PICK_B2] [PICK_B3] [PICK_B4] [PICK_B5] [PICK_R1] [PICK_R2] [PICK_R3] [PICK_R4] [PICK_R5]

Chaque pick = champion_embedding + position_embedding
Le side est ajouté comme embedding global sur toute la sequence Blue/Red.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
from tqdm import tqdm
import mlflow
import mlflow.pytorch
import math
from collections import defaultdict

# ============================================
# CONFIGURATION
# ============================================
CONFIG = {
    # Modèle
    "d_model": 128,  # Dimension des embeddings
    "n_heads": 8,  # Nombre de têtes d'attention
    "n_layers": 4,  # Nombre de couches Transformer
    "d_ff": 512,  # Dimension du feed-forward
    "dropout": 0.3,  # Dropout
    # Entraînement
    "batch_size": 64,
    "learning_rate": 1e-3,
    "weight_decay": 0.01,
    "epochs": 50,
    "warmup_epochs": 5,
    # Données
    "dataset_path": "Dataset/master_dataset.csv",
    "train_ratio": 0.8,
    "val_ratio": 0.1,
    "test_ratio": 0.1,
    # Tâches
    "mask_prob": 0.15,  # Probabilité de masquer un pick pendant l'entraînement
    "win_loss_weight": 1.0,
    "mlm_loss_weight": 0.5,  # Réduit car moins de tokens à prédire
}

# Positions possibles
POSITIONS = ["top", "jng", "mid", "bot", "sup", "unknown"]
SIDES = ["Blue", "Red"]

# Tokens spéciaux
SPECIAL_TOKENS = {
    "[PAD]": 0,
    "[CLS]": 1,
    "[MASK]": 2,
    "[UNK]": 3,
}


# ============================================
# VOCABULAIRE DES CHAMPIONS
# ============================================
class ChampionVocabulary:
    """Gère le mapping champion <-> ID"""

    def __init__(self):
        self.champion_to_id = dict(SPECIAL_TOKENS)
        self.id_to_champion = {v: k for k, v in SPECIAL_TOKENS.items()}
        self.next_id = len(SPECIAL_TOKENS)

    def add_champion(self, champion: str):
        """Ajoute un champion au vocabulaire"""
        if champion not in self.champion_to_id:
            self.champion_to_id[champion] = self.next_id
            self.id_to_champion[self.next_id] = champion
            self.next_id += 1

    def get_id(self, champion: str) -> int:
        """Retourne l'ID d'un champion"""
        return self.champion_to_id.get(champion, SPECIAL_TOKENS["[UNK]"])

    def get_champion(self, id: int) -> str:
        """Retourne le champion à partir de l'ID"""
        return self.id_to_champion.get(id, "[UNK]")

    def __len__(self):
        return self.next_id

    def save(self, path: str):
        """Sauvegarde le vocabulaire"""
        import json

        with open(path, "w") as f:
            json.dump(
                {"champion_to_id": self.champion_to_id, "next_id": self.next_id}, f
            )

    @classmethod
    def load(cls, path: str):
        """Charge un vocabulaire sauvegardé"""
        import json

        with open(path, "r") as f:
            data = json.load(f)
        vocab = cls()
        vocab.champion_to_id = data["champion_to_id"]
        vocab.id_to_champion = {int(v): k for k, v in data["champion_to_id"].items()}
        vocab.next_id = data["next_id"]
        return vocab


# ============================================
# DATASET
# ============================================
class DraftDataset(Dataset):
    """Dataset simplifié - uniquement les picks"""

    def __init__(
        self, df: pd.DataFrame, vocab: ChampionVocabulary, mode: str = "train"
    ):
        """
        Args:
            df: DataFrame avec les drafts (1 ligne = 1 équipe)
            vocab: Vocabulaire des champions
            mode: "train" (avec masking) ou "eval" (sans masking)
        """
        self.vocab = vocab
        self.mode = mode
        self.mask_prob = CONFIG["mask_prob"] if mode == "train" else 0.0

        # Grouper par gameid pour avoir les 2 équipes ensemble
        self.games = []

        for gameid, group in df.groupby("gameid"):
            if len(group) != 2:
                continue

            blue_row = group[group["side"] == "Blue"]
            red_row = group[group["side"] == "Red"]

            if len(blue_row) == 0 or len(red_row) == 0:
                continue

            blue_row = blue_row.iloc[0]
            red_row = red_row.iloc[0]

            self.games.append(
                {
                    "gameid": gameid,
                    "blue": blue_row,
                    "red": red_row,
                    "result": int(blue_row["result"]),  # 1 si Blue gagne
                }
            )

    def __len__(self):
        return len(self.games)

    def parse_pick(self, pick_str):
        """Parse 'Varus.bot' en (champion, position)"""
        if pd.isna(pick_str) or pick_str == "":
            return "[PAD]", "unknown"

        parts = str(pick_str).split(".")
        champion = parts[0]
        position = parts[1].lower() if len(parts) > 1 else "unknown"

        if position not in POSITIONS:
            position = "unknown"

        return champion, position

    def __getitem__(self, idx):
        game = self.games[idx]
        blue = game["blue"]
        red = game["red"]

        # Séquence: [CLS] + 5 picks Blue + 5 picks Red
        champion_ids = [SPECIAL_TOKENS["[CLS]"]]
        position_ids = [0]  # Position pour [CLS]
        side_ids = [0]  # Side pour [CLS] (neutre)

        # Labels pour le masked language modeling
        mlm_labels = [-100]

        # Picks Blue (side_id = 0)
        for i in range(1, 6):
            col = f"pick{i}"
            champ, pos = self.parse_pick(blue[col])

            champ_id = self.vocab.get_id(champ)
            pos_id = (
                POSITIONS.index(pos) if pos in POSITIONS else POSITIONS.index("unknown")
            )

            # Masking aléatoire
            if self.mode == "train" and np.random.random() < self.mask_prob:
                mlm_labels.append(champ_id)
                champ_id = SPECIAL_TOKENS["[MASK]"]
            else:
                mlm_labels.append(-100)

            champion_ids.append(champ_id)
            position_ids.append(pos_id)
            side_ids.append(0)  # Blue = 0

        # Picks Red (side_id = 1)
        for i in range(1, 6):
            col = f"pick{i}"
            champ, pos = self.parse_pick(red[col])

            champ_id = self.vocab.get_id(champ)
            pos_id = (
                POSITIONS.index(pos) if pos in POSITIONS else POSITIONS.index("unknown")
            )

            # Masking aléatoire
            if self.mode == "train" and np.random.random() < self.mask_prob:
                mlm_labels.append(champ_id)
                champ_id = SPECIAL_TOKENS["[MASK]"]
            else:
                mlm_labels.append(-100)

            champion_ids.append(champ_id)
            position_ids.append(pos_id)
            side_ids.append(1)  # Red = 1

        return {
            "champion_ids": torch.tensor(champion_ids, dtype=torch.long),
            "position_ids": torch.tensor(position_ids, dtype=torch.long),
            "side_ids": torch.tensor(side_ids, dtype=torch.long),
            "mlm_labels": torch.tensor(mlm_labels, dtype=torch.long),
            "win_label": torch.tensor(game["result"], dtype=torch.float),
        }


# ============================================
# POSITIONAL ENCODING
# ============================================
class PositionalEncoding(nn.Module):
    """Encoding positionnel sinusoïdal"""

    def __init__(self, d_model: int, max_len: int = 50):
        super().__init__()

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)

        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, : x.size(1)]


# ============================================
# DRAFT TRANSFORMER (SIMPLIFIÉ)
# ============================================
class DraftTransformer(nn.Module):
    """
    Transformer simplifié pour la prédiction de draft

    Input: [CLS] + 5 picks Blue + 5 picks Red = 11 tokens
    Output:
        - Win Prediction (probabilité Blue gagne)
        - Champion Prediction pour les [MASK]
    """

    def __init__(
        self,
        vocab_size: int,
        n_positions: int = 6,  # top, jng, mid, bot, sup, unknown
        n_sides: int = 2,  # Blue, Red
    ):
        super().__init__()

        d_model = CONFIG["d_model"]

        # Embeddings
        self.champion_embedding = nn.Embedding(
            vocab_size, d_model, padding_idx=SPECIAL_TOKENS["[PAD]"]
        )
        self.position_embedding = nn.Embedding(n_positions, d_model // 2)
        self.side_embedding = nn.Embedding(n_sides + 1, d_model // 2)  # +1 pour [CLS]

        # Projection pour combiner les embeddings
        self.input_projection = nn.Linear(
            d_model + d_model // 2 + d_model // 2, d_model
        )

        # Positional encoding
        self.pos_encoding = PositionalEncoding(d_model)

        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=CONFIG["n_heads"],
            dim_feedforward=CONFIG["d_ff"],
            dropout=CONFIG["dropout"],
            batch_first=True,
            activation="gelu",
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer, num_layers=CONFIG["n_layers"]
        )

        # Tête de prédiction de victoire (sur [CLS])
        self.win_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(CONFIG["dropout"]),
            nn.Linear(d_model // 2, 1),
        )

        # Tête de prédiction de champion (MLM)
        self.mlm_head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model),
            nn.Linear(d_model, vocab_size),
        )

        self.dropout = nn.Dropout(CONFIG["dropout"])
        self._init_weights()

    def _init_weights(self):
        """Initialisation Xavier/Glorot"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0, std=0.02)

    def forward(self, champion_ids, position_ids, side_ids, attention_mask=None):
        """
        Args:
            champion_ids: (batch, 11) - IDs des champions
            position_ids: (batch, 11) - IDs des positions
            side_ids: (batch, 11) - IDs des sides (0=Blue, 1=Red)
            attention_mask: (batch, 11) - Masque d'attention (optionnel)

        Returns:
            win_logits: (batch, 1) - Logits pour la victoire Blue
            mlm_logits: (batch, 11, vocab_size) - Logits pour chaque champion
        """
        # Embeddings
        champ_emb = self.champion_embedding(champion_ids)
        pos_emb = self.position_embedding(position_ids)
        side_emb = self.side_embedding(side_ids)

        # Concaténer et projeter
        combined = torch.cat([champ_emb, pos_emb, side_emb], dim=-1)
        x = self.input_projection(combined)

        # Positional encoding et dropout
        x = self.pos_encoding(x)
        x = self.dropout(x)

        # Transformer
        if attention_mask is not None:
            attention_mask = ~attention_mask.bool()

        x = self.transformer(x, src_key_padding_mask=attention_mask)

        # Prédiction de victoire (sur le token [CLS])
        cls_output = x[:, 0]
        win_logits = self.win_head(cls_output)

        # Prédiction MLM
        mlm_logits = self.mlm_head(x)

        return win_logits, mlm_logits

    def predict_win(self, champion_ids, position_ids, side_ids):
        """Prédit la probabilité de victoire Blue"""
        win_logits, _ = self.forward(champion_ids, position_ids, side_ids)
        return torch.sigmoid(win_logits)

    def suggest_champion(
        self,
        champion_ids,
        position_ids,
        side_ids,
        mask_position: int,
        top_k: int = 5,
        excluded_ids: list = None,
    ):
        """
        Suggère les meilleurs champions pour une position masquée

        Args:
            mask_position: Index du token [MASK] dans la séquence (1-10)
            top_k: Nombre de suggestions
            excluded_ids: IDs de champions à exclure (déjà pickés/bannés)
        """
        _, mlm_logits = self.forward(champion_ids, position_ids, side_ids)

        # Probabilités pour la position masquée
        logits = mlm_logits[:, mask_position]

        # Exclure les champions déjà utilisés
        if excluded_ids:
            for idx in excluded_ids:
                logits[:, idx] = float("-inf")

        # Exclure les tokens spéciaux
        for token_id in SPECIAL_TOKENS.values():
            logits[:, token_id] = float("-inf")

        probs = F.softmax(logits, dim=-1)
        top_probs, top_ids = torch.topk(probs, top_k, dim=-1)

        return list(zip(top_ids[0].tolist(), top_probs[0].tolist()))


# ============================================
# FONCTIONS D'ENTRAÎNEMENT
# ============================================
def train_one_epoch(model, dataloader, optimizer, scheduler, device, vocab_size):
    """Entraîne le modèle pour une epoch"""
    model.train()
    total_loss = 0
    total_win_loss = 0
    total_mlm_loss = 0
    correct_wins = 0
    total_wins = 0

    win_criterion = nn.BCEWithLogitsLoss()
    mlm_criterion = nn.CrossEntropyLoss(ignore_index=-100)

    for batch in tqdm(dataloader, desc="Training", leave=False):
        champion_ids = batch["champion_ids"].to(device)
        position_ids = batch["position_ids"].to(device)
        side_ids = batch["side_ids"].to(device)
        mlm_labels = batch["mlm_labels"].to(device)
        win_labels = batch["win_label"].to(device)

        win_logits, mlm_logits = model(champion_ids, position_ids, side_ids)

        # Losses
        win_loss = win_criterion(win_logits.squeeze(-1), win_labels)
        mlm_loss = mlm_criterion(mlm_logits.view(-1, vocab_size), mlm_labels.view(-1))

        loss = (
            CONFIG["win_loss_weight"] * win_loss + CONFIG["mlm_loss_weight"] * mlm_loss
        )

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()
        total_win_loss += win_loss.item()
        total_mlm_loss += mlm_loss.item()

        win_preds = (torch.sigmoid(win_logits.squeeze(-1)) > 0.5).float()
        correct_wins += (win_preds == win_labels).sum().item()
        total_wins += len(win_labels)

    n_batches = len(dataloader)
    return {
        "loss": total_loss / n_batches,
        "win_loss": total_win_loss / n_batches,
        "mlm_loss": total_mlm_loss / n_batches,
        "win_accuracy": correct_wins / total_wins,
    }


def evaluate(model, dataloader, device, vocab_size):
    """Évalue le modèle"""
    model.eval()
    total_loss = 0
    correct_wins = 0
    total_wins = 0

    win_criterion = nn.BCEWithLogitsLoss()

    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Evaluating", leave=False):
            champion_ids = batch["champion_ids"].to(device)
            position_ids = batch["position_ids"].to(device)
            side_ids = batch["side_ids"].to(device)
            win_labels = batch["win_label"].to(device)

            win_logits, _ = model(champion_ids, position_ids, side_ids)
            win_loss = win_criterion(win_logits.squeeze(-1), win_labels)

            total_loss += win_loss.item()

            win_preds = (torch.sigmoid(win_logits.squeeze(-1)) > 0.5).float()
            correct_wins += (win_preds == win_labels).sum().item()
            total_wins += len(win_labels)

    n_batches = len(dataloader)
    return {
        "loss": total_loss / n_batches,
        "win_accuracy": correct_wins / total_wins,
    }


# ============================================
# MAIN
# ============================================
def main():
    print("=" * 60)
    print("DRAFT TRANSFORMER (SIMPLIFIÉ) - Entraînement")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n🖥️  Device: {device}")
    if device.type == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")

    # Charger les données
    print(f"\n📂 Chargement du dataset: {CONFIG['dataset_path']}")
    df = pd.read_csv(CONFIG["dataset_path"], low_memory=False)
    print(f"   Lignes: {len(df):,}")

    # Construire le vocabulaire (uniquement les picks maintenant)
    print("\n📚 Construction du vocabulaire...")
    vocab = ChampionVocabulary()

    for col in ["pick1", "pick2", "pick3", "pick4", "pick5"]:
        if col in df.columns:
            for val in df[col].dropna().unique():
                champ = str(val).split(".")[0]
                vocab.add_champion(champ)

    print(f"   Champions: {len(vocab) - len(SPECIAL_TOKENS)}")
    print(f"   Vocab total: {len(vocab)}")

    # Sauvegarder le vocabulaire
    vocab.save("vocab.json")
    print("   Vocabulaire sauvegardé: vocab.json")

    # Split train/val/test
    print("\n✂️  Split des données...")
    game_ids = df["gameid"].unique()
    np.random.seed(42)
    np.random.shuffle(game_ids)

    n_train = int(len(game_ids) * CONFIG["train_ratio"])
    n_val = int(len(game_ids) * CONFIG["val_ratio"])

    train_ids = set(game_ids[:n_train])
    val_ids = set(game_ids[n_train : n_train + n_val])
    test_ids = set(game_ids[n_train + n_val :])

    train_df = df[df["gameid"].isin(train_ids)]
    val_df = df[df["gameid"].isin(val_ids)]
    test_df = df[df["gameid"].isin(test_ids)]

    print(f"   Train: {len(train_ids):,} games")
    print(f"   Val: {len(val_ids):,} games")
    print(f"   Test: {len(test_ids):,} games")

    # Datasets
    train_dataset = DraftDataset(train_df, vocab, mode="train")
    val_dataset = DraftDataset(val_df, vocab, mode="eval")
    test_dataset = DraftDataset(test_df, vocab, mode="eval")

    train_loader = DataLoader(
        train_dataset, batch_size=CONFIG["batch_size"], shuffle=True, num_workers=0
    )
    val_loader = DataLoader(
        val_dataset, batch_size=CONFIG["batch_size"], shuffle=False, num_workers=0
    )
    test_loader = DataLoader(
        test_dataset, batch_size=CONFIG["batch_size"], shuffle=False, num_workers=0
    )

    # Modèle
    print("\n🧠 Création du modèle...")
    model = DraftTransformer(vocab_size=len(vocab)).to(device)

    n_params = sum(p.numel() for p in model.parameters())
    print(f"   Paramètres: {n_params:,}")
    print(f"   Séquence: [CLS] + 5 Blue + 5 Red = 11 tokens")

    # Optimizer et Scheduler
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=CONFIG["learning_rate"],
        weight_decay=CONFIG["weight_decay"],
    )

    total_steps = len(train_loader) * CONFIG["epochs"]
    warmup_steps = len(train_loader) * CONFIG["warmup_epochs"]

    def lr_lambda(step):
        if step < warmup_steps:
            return step / warmup_steps
        progress = (step - warmup_steps) / (total_steps - warmup_steps)
        return 0.5 * (1 + math.cos(math.pi * progress))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # MLflow
    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment("draft-transformer-simple")

    print("\n" + "=" * 60)
    print("ENTRAÎNEMENT")
    print("=" * 60)

    best_val_acc = 0.0

    with mlflow.start_run():
        mlflow.log_params(CONFIG)
        mlflow.log_param("vocab_size", len(vocab))
        mlflow.log_param("n_params", n_params)
        mlflow.log_param("seq_length", 11)

        for epoch in range(1, CONFIG["epochs"] + 1):
            print(f"\n📅 Epoch {epoch}/{CONFIG['epochs']}")

            train_metrics = train_one_epoch(
                model, train_loader, optimizer, scheduler, device, len(vocab)
            )
            val_metrics = evaluate(model, val_loader, device, len(vocab))

            print(
                f"   Train - Loss: {train_metrics['loss']:.4f} | "
                f"Win Acc: {train_metrics['win_accuracy']*100:.1f}%"
            )
            print(
                f"   Val   - Loss: {val_metrics['loss']:.4f} | "
                f"Win Acc: {val_metrics['win_accuracy']*100:.1f}%"
            )

            mlflow.log_metrics(
                {
                    "train_loss": train_metrics["loss"],
                    "train_win_acc": train_metrics["win_accuracy"],
                    "val_loss": val_metrics["loss"],
                    "val_win_acc": val_metrics["win_accuracy"],
                    "lr": scheduler.get_last_lr()[0],
                },
                step=epoch,
            )

            if val_metrics["win_accuracy"] > best_val_acc:
                best_val_acc = val_metrics["win_accuracy"]
                torch.save(
                    {
                        "epoch": epoch,
                        "model_state_dict": model.state_dict(),
                        "config": CONFIG,
                        "vocab_size": len(vocab),
                    },
                    "best_draft_transformer.pt",
                )
                print(
                    f"   💾 Meilleur modèle sauvegardé! (Val Acc: {best_val_acc*100:.1f}%)"
                )

        # Test final
        print("\n" + "=" * 60)
        print("ÉVALUATION FINALE (Test Set)")
        print("=" * 60)

        checkpoint = torch.load("best_draft_transformer.pt", weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])

        test_metrics = evaluate(model, test_loader, device, len(vocab))
        print(f"\n🎯 Test Win Accuracy: {test_metrics['win_accuracy']*100:.1f}%")

        mlflow.log_metric("test_win_acc", test_metrics["win_accuracy"])
        mlflow.pytorch.log_model(model, "model")

    print("\n✅ Entraînement terminé!")
    print(f"   Meilleure Val Accuracy: {best_val_acc*100:.1f}%")
    print(f"   Test Accuracy: {test_metrics['win_accuracy']*100:.1f}%")


if __name__ == "__main__":
    main()
