# Projet DevOps Riot

Application de consultation et analyse de drafts League of Legends utilisant l'API Riot Games.

## 📋 Description

Ce projet permet de :
- **Collecter** des données de parties ranked depuis l'API Riot Games
- **Analyser** les compositions d'équipes (drafts) et les bans
- **Consulter** les statistiques de jeu via une interface web

## 🏗️ Architecture du Projet

```
projet_devops_riot/
├── riot.py                 # Script Python - Collecte de données API Riot
├── drafts_data.json        # Données de drafts collectées (JSON)
├── README.md               # Documentation principale
│
└── riot/                   # Application Frontend Vue.js
    ├── src/
    │   ├── App.vue         # Composant racine
    │   ├── main.ts         # Point d'entrée de l'application
    │   ├── components/     # Composants Vue réutilisables
    │   ├── views/          # Pages de l'application
    │   │   ├── HomeView.vue
    │   │   └── AboutView.vue
    │   ├── router/         # Configuration du routage (Vue Router)
    │   ├── stores/         # État global (Pinia)
    │   └── assets/         # Fichiers CSS et ressources statiques
    ├── e2e/                # Tests End-to-End (Playwright)
    ├── public/             # Fichiers statiques publics
    └── package.json        # Dépendances et scripts npm
```

## 🛠️ Technologies Utilisées

### Backend / Data Collection
| Technologie | Version | Usage |
|-------------|---------|-------|
| Python | 3.x | Script de collecte de données |
| Riot API | v5 | Source des données de match |

### Frontend
| Technologie | Version | Usage |
|-------------|---------|-------|
| Vue.js | 3.5 | Framework frontend |
| TypeScript | 5.9 | Typage statique |
| Vite | 7.3 | Build tool & dev server |
| Vue Router | 4.6 | Navigation SPA |
| Pinia | 3.0 | State management |

### Tests & Qualité
| Outil | Usage |
|-------|-------|
| Vitest | Tests unitaires |
| Playwright | Tests E2E |
| ESLint | Linting |
| Prettier | Formatage du code |

## 🚀 Installation & Démarrage

### Prérequis
- Node.js >= 20.19.0 ou >= 22.12.0
- Python 3.x
- Clé API Riot Games (https://developer.riotgames.com/)

### Backend (Collecte de données)

```bash
# Installer les dépendances Python
pip install requests

# Configurer votre clé API dans riot.py
# API_KEY = "VOTRE_CLE_API"

# Lancer la collecte
python riot.py
```

### Frontend (Application Vue.js)

```bash
# Se placer dans le dossier frontend
cd riot

# Installer les dépendances
npm install

# Lancer en mode développement
npm run dev

# Build pour la production
npm run build
```

## 📝 Scripts Disponibles

| Commande | Description |
|----------|-------------|
| `npm run dev` | Lance le serveur de développement |
| `npm run build` | Compile pour la production |
| `npm run preview` | Prévisualise le build de production |
| `npm run test:unit` | Exécute les tests unitaires (Vitest) |
| `npm run test:e2e` | Exécute les tests E2E (Playwright) |
| `npm run lint` | Analyse et corrige le code (ESLint) |
| `npm run format` | Formate le code (Prettier) |

## 🎮 API Riot Games

Le script `riot.py` utilise les endpoints suivants :
- **Account API** : Récupération du PUUID via Riot ID
- **Match API v5** : Historique et détails des parties

### Données collectées
- Composition des équipes (champions, positions)
- Bans de chaque équipe
- Résultat de la partie
- Version du jeu et durée

### Rate Limiting
Le script respecte les limites de l'API Riot (~100 requêtes/min) avec un délai de 1.2s entre chaque requête.

## 🔧 Configuration IDE Recommandée

- [VS Code](https://code.visualstudio.com/)
- [Extension Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar)
- Vue.js DevTools pour navigateur

## 📄 Licence

Projet éducatif - DevOps