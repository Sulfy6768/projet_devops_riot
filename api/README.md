# Riot DevOps API

API FastAPI pour l'analyse de drafts League of Legends et prédictions IA.

## 🚀 Fonctionnalités

- Récupération des données de drafts
- Intégration avec MLflow pour les prédictions
- Métriques Prometheus exposées sur `/metrics`
- Health check sur `/health`

## 📦 Installation locale

```bash
# Avec uv
uv sync

# Lancer l'API
fastapi dev
```

## 🐳 Docker

```bash
docker build -t riot-api .
docker run -p 8000:8000 riot-api
```

## 📚 Documentation API

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔗 Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Page d'accueil |
| `GET /health` | Health check |
| `GET /metrics` | Métriques Prometheus |
| `GET /api/v1/drafts` | Liste des drafts |
| `GET /api/v1/champions` | Liste des champions |
| `GET /api/v1/predictions/draft` | Prédiction de draft |
