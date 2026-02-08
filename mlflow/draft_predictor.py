"""
Draft Predictor - Chargement et Test du Modèle Simplifié
=========================================================

Ce script permet de :
1. Charger un modèle entraîné
2. Prédire le winrate d'une draft (basé uniquement sur les picks)
3. Suggérer les meilleurs picks

Usage :
    python draft_predictor.py
"""

import torch
import torch.nn.functional as F
import pandas as pd
from draft_transformer import (
    DraftTransformer,
    ChampionVocabulary,
    SPECIAL_TOKENS,
    POSITIONS,
    CONFIG,
)

# Constantes pour les sides
BLUE_SIDE_ID = 0
RED_SIDE_ID = 1

# Mapping des noms de champions du frontend vers les noms du vocabulaire
# Frontend utilise PascalCase sans espaces, vocab utilise des espaces et apostrophes
CHAMPION_NAME_MAP = {
    # Noms avec espaces
    "leesin": "Lee Sin",
    "jarvaniv": "Jarvan IV",
    "xinzhao": "Xin Zhao",
    "missfortune": "Miss Fortune",
    "masteryi": "Master Yi",
    "tahmkench": "Tahm Kench",
    "twistedfate": "Twisted Fate",
    "aurelionsol": "Aurelion Sol",
    "drmundo": "Dr. Mundo",
    "renataglasc": "Renata Glasc",
    # Noms avec apostrophes
    "reksai": "Rek'Sai",
    "khazix": "Kha'Zix",
    "chogath": "Cho'Gath",
    "kogmaw": "Kog'Maw",
    "velkoz": "Vel'Koz",
    "kaisa": "Kai'Sa",
    "belveth": "Bel'Veth",
    "ksante": "K'Sante",
    # Autres cas spéciaux
    "nunu": "Nunu & Willump",
    "wukong": "Wukong",
    "monkeyking": "Wukong",
    "leblanc": "LeBlanc",
    "fiddlesticks": "Fiddlesticks",
}


def normalize_champion_name(name: str) -> str:
    """
    Normalise un nom de champion du format frontend vers le format vocabulaire.
    
    Ex: "LeeSin" -> "Lee Sin", "KhaZix" -> "Kha'Zix"
    """
    if not name:
        return name
    
    # Essayer le mapping direct (en minuscules)
    lower_name = name.lower().replace("'", "").replace(" ", "").replace(".", "")
    if lower_name in CHAMPION_NAME_MAP:
        return CHAMPION_NAME_MAP[lower_name]
    
    # Sinon retourner le nom original (peut déjà être correct)
    return name


class DraftPredictor:
    """
    Classe pour charger et utiliser le modèle Draft Transformer simplifié

    Le modèle prend en entrée uniquement les picks (pas de bans):
    - 5 picks Blue avec position
    - 5 picks Red avec position
    """

    def __init__(
        self,
        model_path: str = "best_draft_transformer.pt",
        vocab_path: str = "vocab.json",
    ):
        """
        Charge le modèle depuis un checkpoint

        Args:
            model_path: Chemin vers le fichier .pt
            vocab_path: Chemin vers le vocabulaire JSON
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🖥️  Device: {self.device}")

        # Charger le checkpoint
        print(f"📂 Chargement du modèle: {model_path}")
        checkpoint = torch.load(
            model_path, map_location=self.device, weights_only=False
        )

        # Charger le vocabulaire
        self.vocab = ChampionVocabulary.load(vocab_path)
        self.config = checkpoint.get("config", CONFIG)

        # Recréer le modèle
        vocab_size = checkpoint.get("vocab_size", len(self.vocab))
        self.model = DraftTransformer(vocab_size=vocab_size).to(self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

        print(f"✅ Modèle chargé! (Epoch {checkpoint.get('epoch', '?')})")
        print(f"   Vocab: {len(self.vocab)} tokens")

    def _parse_pick(self, pick_str: str):
        """Parse 'Varus.bot' en (champion, position) avec normalisation du nom"""
        if pd.isna(pick_str) or pick_str == "" or pick_str is None:
            return "[PAD]", "unknown"

        parts = str(pick_str).split(".")
        champion = parts[0]
        position = parts[1].lower() if len(parts) > 1 else "unknown"

        if position not in POSITIONS:
            position = "unknown"

        # Normaliser le nom du champion pour correspondre au vocabulaire
        champion = normalize_champion_name(champion)

        return champion, position

    def _build_sequence(self, draft: dict, mask_index: int = None):
        """
        Construit la séquence d'entrée pour le modèle

        Args:
            draft: Dict avec les clés:
                - blue_picks: ["Champion1.pos", "Champion2.pos", ...]
                - red_picks: ["Champion1.pos", "Champion2.pos", ...]
            mask_index: Index du pick à masquer (1-10, 1-5 pour Blue, 6-10 pour Red)

        Returns:
            Dict avec les tenseurs d'entrée
        """
        champion_ids = [SPECIAL_TOKENS["[CLS]"]]
        position_ids = [0]  # Position pour [CLS]
        side_ids = [BLUE_SIDE_ID]  # Side pour [CLS] (neutre, on met Blue par défaut)

        # Picks Blue (indices 1-5)
        blue_picks = draft.get("blue_picks", [])
        for i in range(5):
            pick_str = blue_picks[i] if i < len(blue_picks) else None
            champ, pos = self._parse_pick(pick_str)

            # Masquer si demandé
            if mask_index is not None and mask_index == i + 1:
                champ_id = SPECIAL_TOKENS["[MASK]"]
            else:
                champ_id = (
                    self.vocab.get_id(champ)
                    if champ != "[PAD]"
                    else SPECIAL_TOKENS["[PAD]"]
                )

            pos_id = (
                POSITIONS.index(pos) if pos in POSITIONS else POSITIONS.index("unknown")
            )

            champion_ids.append(champ_id)
            position_ids.append(pos_id)
            side_ids.append(BLUE_SIDE_ID)

        # Picks Red (indices 6-10)
        red_picks = draft.get("red_picks", [])
        for i in range(5):
            pick_str = red_picks[i] if i < len(red_picks) else None
            champ, pos = self._parse_pick(pick_str)

            # Masquer si demandé
            if mask_index is not None and mask_index == i + 6:
                champ_id = SPECIAL_TOKENS["[MASK]"]
            else:
                champ_id = (
                    self.vocab.get_id(champ)
                    if champ != "[PAD]"
                    else SPECIAL_TOKENS["[PAD]"]
                )

            pos_id = (
                POSITIONS.index(pos) if pos in POSITIONS else POSITIONS.index("unknown")
            )

            champion_ids.append(champ_id)
            position_ids.append(pos_id)
            side_ids.append(RED_SIDE_ID)

        return {
            "champion_ids": torch.tensor([champion_ids], dtype=torch.long).to(
                self.device
            ),
            "position_ids": torch.tensor([position_ids], dtype=torch.long).to(
                self.device
            ),
            "side_ids": torch.tensor([side_ids], dtype=torch.long).to(self.device),
        }

    def predict_win(self, draft: dict) -> float:
        """
        Prédit la probabilité de victoire de Blue

        Args:
            draft: Dict avec blue_picks, red_picks (format "Champion.position")

        Returns:
            Probabilité de victoire Blue (0-1)
        """
        inputs = self._build_sequence(draft)

        with torch.no_grad():
            win_logits, _ = self.model(**inputs)
            win_prob = torch.sigmoid(win_logits).item()

        return win_prob

    def suggest_champion(
        self,
        draft: dict,
        position_index: int,  # 1-10 (1-5 Blue, 6-10 Red)
        role: str = "unknown",
        top_k: int = 10,
        exclude_picked: bool = True,
    ):
        """
        Suggère les meilleurs champions pour une position

        Args:
            draft: Draft actuelle (peut être partielle)
            position_index: Position dans la séquence (1-5 pour Blue, 6-10 pour Red)
            role: Rôle attendu (top, jng, mid, bot, sup)
            top_k: Nombre de suggestions
            exclude_picked: Exclure les champions déjà pick

        Returns:
            Liste de dict avec champion et probabilité
        """
        if position_index < 1 or position_index > 10:
            raise ValueError("position_index doit être entre 1 et 10")

        side = "Blue" if position_index <= 5 else "Red"

        # Construire la séquence avec un MASK à la position demandée
        inputs = self._build_sequence(draft, mask_index=position_index)

        with torch.no_grad():
            _, mlm_logits = self.model(**inputs)
            probs = F.softmax(mlm_logits[0, position_index], dim=-1)

        # Exclure les champions déjà utilisés
        if exclude_picked:
            used_champs = set()
            for picks in [draft.get("blue_picks", []), draft.get("red_picks", [])]:
                for p in picks:
                    if p:
                        champ, _ = self._parse_pick(p)
                        used_champs.add(champ)

            for champ in used_champs:
                champ_id = self.vocab.get_id(champ)
                if champ_id < len(probs):
                    probs[champ_id] = 0.0

            # Exclure les tokens spéciaux
            for token_id in SPECIAL_TOKENS.values():
                probs[token_id] = 0.0

        # Top-k
        top_probs, top_ids = torch.topk(probs, top_k)

        suggestions = []
        for prob, champ_id in zip(top_probs.tolist(), top_ids.tolist()):
            champ_name = self.vocab.get_champion(champ_id)
            suggestions.append(
                {
                    "champion": champ_name,
                    "probability": prob,
                    "side": side,
                    "role": role,
                }
            )

        return suggestions

    def complete_draft(self, blue_picks=None, red_picks=None):
        """
        Complète une draft partielle en suggérant les picks manquants

        Returns:
            Draft complète avec les suggestions
        """
        draft = {
            "blue_picks": list(blue_picks) if blue_picks else [],
            "red_picks": list(red_picks) if red_picks else [],
        }

        print("\n🎮 Complétion de draft")
        print("=" * 50)

        # Rôles dans l'ordre standard
        roles = ["top", "jng", "mid", "bot", "sup"]

        # Compléter les picks Blue
        for i in range(5):
            if i < len(draft["blue_picks"]) and draft["blue_picks"][i]:
                champ, pos = self._parse_pick(draft["blue_picks"][i])
                print(f"  Blue {i+1} ({roles[i]}): {champ} (existant)")
            else:
                suggestions = self.suggest_champion(
                    draft, i + 1, role=roles[i], top_k=5
                )
                best = suggestions[0]
                pick = f"{best['champion']}.{roles[i]}"

                # Ajouter ou remplacer
                if i < len(draft["blue_picks"]):
                    draft["blue_picks"][i] = pick
                else:
                    draft["blue_picks"].append(pick)

                print(
                    f"  Blue {i+1} ({roles[i]}): {best['champion']} ({best['probability']*100:.1f}%)"
                )

        # Compléter les picks Red
        for i in range(5):
            if i < len(draft["red_picks"]) and draft["red_picks"][i]:
                champ, pos = self._parse_pick(draft["red_picks"][i])
                print(f"  Red {i+1} ({roles[i]}): {champ} (existant)")
            else:
                suggestions = self.suggest_champion(
                    draft, i + 6, role=roles[i], top_k=5
                )
                best = suggestions[0]
                pick = f"{best['champion']}.{roles[i]}"

                if i < len(draft["red_picks"]):
                    draft["red_picks"][i] = pick
                else:
                    draft["red_picks"].append(pick)

                print(
                    f"  Red {i+1} ({roles[i]}): {best['champion']} ({best['probability']*100:.1f}%)"
                )

        # Prédiction finale
        win_prob = self.predict_win(draft)
        print("\n" + "=" * 50)
        print(f"📊 Prédiction: Blue {win_prob*100:.1f}% - Red {(1-win_prob)*100:.1f}%")

        return draft, win_prob


def print_draft(draft: dict):
    """Affiche une draft de manière lisible"""
    print("\n" + "=" * 50)
    print("📋 DRAFT (Picks uniquement)")
    print("=" * 50)

    print("\n🔵 BLUE SIDE")
    picks = draft.get("blue_picks", [])
    for i, p in enumerate(picks, 1):
        if p:
            champ, pos = p.rsplit(".", 1) if "." in p else (p, "?")
            print(f"   Pick {i} ({pos}): {champ}")
        else:
            print(f"   Pick {i}: (vide)")

    print("\n🔴 RED SIDE")
    picks = draft.get("red_picks", [])
    for i, p in enumerate(picks, 1):
        if p:
            champ, pos = p.rsplit(".", 1) if "." in p else (p, "?")
            print(f"   Pick {i} ({pos}): {champ}")
        else:
            print(f"   Pick {i}: (vide)")


# ============================================
# TESTS
# ============================================
def test_win_prediction(predictor: DraftPredictor):
    """Test de prédiction de victoire"""
    print("\n" + "=" * 60)
    print("TEST 1: Prédiction de victoire")
    print("=" * 60)

    draft = {
        "blue_picks": [
            "Ksante.top",
            "Viego.jng",
            "Syndra.mid",
            "Jinx.bot",
            "Thresh.sup",
        ],
        "red_picks": [
            "Gnar.top",
            "Lee Sin.jng",
            "Ahri.mid",
            "Ezreal.bot",
            "Nautilus.sup",
        ],
    }

    print_draft(draft)

    win_prob = predictor.predict_win(draft)
    print(f"\n🎯 Prédiction: Blue {win_prob*100:.1f}% - Red {(1-win_prob)*100:.1f}%")


def test_champion_suggestion(predictor: DraftPredictor):
    """Test de suggestion de champion"""
    print("\n" + "=" * 60)
    print("TEST 2: Suggestion de champion")
    print("=" * 60)

    draft = {
        "blue_picks": ["Ksante.top", "Viego.jng"],
        "red_picks": ["Gnar.top"],
    }

    print("\nDraft actuelle:")
    print_draft(draft)

    # Suggérer le mid Blue (position 3)
    print(f"\n🎯 Suggestions pour Blue mid (pick 3):")
    suggestions = predictor.suggest_champion(
        draft, position_index=3, role="mid", top_k=10
    )

    for i, s in enumerate(suggestions, 1):
        print(f"  {i:2d}. {s['champion']:15s} - {s['probability']*100:.1f}%")


def test_complete_draft(predictor: DraftPredictor):
    """Test de complétion de draft"""
    print("\n" + "=" * 60)
    print("TEST 3: Complétion de draft")
    print("=" * 60)

    # Draft partielle
    blue_picks = ["Ksante.top", "Viego.jng"]
    red_picks = ["Gnar.top", "Lee Sin.jng", "Ahri.mid"]

    draft, win_prob = predictor.complete_draft(blue_picks, red_picks)
    print_draft(draft)


def interactive_mode(predictor: DraftPredictor):
    """Mode interactif pour tester le modèle"""
    print("\n" + "=" * 60)
    print("MODE INTERACTIF")
    print("=" * 60)
    print("\nCommandes:")
    print("  win             - Prédire le winrate")
    print("  suggest <1-10>  - Suggérer un champion (1-5 Blue, 6-10 Red)")
    print("  complete        - Compléter la draft")
    print("  blue <n> <champ.pos> - Définir pick Blue n")
    print("  red <n> <champ.pos>  - Définir pick Red n")
    print("  reset           - Réinitialiser la draft")
    print("  quit            - Quitter")

    draft = {
        "blue_picks": [None] * 5,
        "red_picks": [None] * 5,
    }

    while True:
        print("\n" + "-" * 40)
        print_draft(draft)

        cmd = input("\n> ").strip()
        cmd_lower = cmd.lower()

        if cmd_lower == "quit" or cmd_lower == "q":
            break

        elif cmd_lower == "complete":
            # Nettoyer les None
            bp = [p for p in draft["blue_picks"] if p]
            rp = [p for p in draft["red_picks"] if p]
            draft, _ = predictor.complete_draft(bp, rp)

        elif cmd_lower == "win":
            win_prob = predictor.predict_win(draft)
            print(f"\n🎯 Blue {win_prob*100:.1f}% - Red {(1-win_prob)*100:.1f}%")

        elif cmd_lower.startswith("suggest"):
            parts = cmd.split()
            pos = int(parts[1]) if len(parts) > 1 else 1
            role = parts[2] if len(parts) > 2 else "unknown"
            suggestions = predictor.suggest_champion(draft, pos, role=role, top_k=5)
            side = "Blue" if pos <= 5 else "Red"
            print(f"\nSuggestions pour {side} pick {pos if pos <= 5 else pos - 5}:")
            for i, s in enumerate(suggestions, 1):
                print(f"  {i}. {s['champion']} ({s['probability']*100:.1f}%)")

        elif cmd_lower.startswith("blue "):
            parts = cmd.split(maxsplit=2)
            if len(parts) >= 3:
                n = int(parts[1]) - 1
                pick = parts[2]
                if 0 <= n < 5:
                    draft["blue_picks"][n] = pick
                    print(f"  ✓ Blue pick {n+1} = {pick}")

        elif cmd_lower.startswith("red "):
            parts = cmd.split(maxsplit=2)
            if len(parts) >= 3:
                n = int(parts[1]) - 1
                pick = parts[2]
                if 0 <= n < 5:
                    draft["red_picks"][n] = pick
                    print(f"  ✓ Red pick {n+1} = {pick}")

        elif cmd_lower == "reset":
            draft = {"blue_picks": [None] * 5, "red_picks": [None] * 5}
            print("  ✓ Draft réinitialisée")

        elif cmd_lower == "help":
            print(
                "\nCommandes: win, suggest <pos>, complete, blue/red <n> <pick>, reset, quit"
            )

        else:
            print("❓ Commande non reconnue. Tape 'help' pour l'aide.")


# ============================================
# MAIN
# ============================================
def main():
    print("=" * 60)
    print("DRAFT PREDICTOR (SIMPLIFIÉ) - Test & Prédiction")
    print("=" * 60)

    # Charger le modèle
    predictor = DraftPredictor("best_draft_transformer.pt", "vocab.json")

    # Tests
    test_win_prediction(predictor)
    test_champion_suggestion(predictor)
    test_complete_draft(predictor)

    # Mode interactif
    print("\n" + "=" * 60)
    response = input("\nLancer le mode interactif? (y/n): ")
    if response.lower() == "y":
        interactive_mode(predictor)


if __name__ == "__main__":
    main()
