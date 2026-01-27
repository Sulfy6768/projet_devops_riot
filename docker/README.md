# 🐳 Infrastructure Docker - Projet Riot DevOps

## Vue d'ensemble

Cette infrastructure Docker fournit les services nécessaires pour le monitoring et la gestion des modèles IA.

## Services

| Service | Port | Description |
|---------|------|-------------|
| **Grafana** | 3001 | Dashboards et visualisation |
| **Prometheus** | 9090 | Collecte et stockage des métriques |
| **MLflow** | 5000 | Tracking des expériences ML |
| **Node Exporter** | 9100 | Métriques système |

## Démarrage rapide

```bash
# Démarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter les services
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v
```

## Accès aux interfaces

- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **MLflow**: http://localhost:5000

## Structure des dossiers

```
docker/
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/    # Config auto des sources de données
│   │   └── dashboards/     # Config auto des dashboards
│   └── dashboards/         # Fichiers JSON des dashboards
├── prometheus/
│   ├── prometheus.yml      # Configuration principale
│   └── alerts.yml          # Règles d'alertes
└── README.md
```

## Dashboards disponibles

### System Metrics
- Utilisation CPU, RAM, Disque
- État des services (UP/DOWN)
- Graphiques temporels

### MLflow Monitoring
- État du serveur MLflow
- Guide des métriques à tracker
- Liens vers l'UI MLflow

## Ajouter un nouveau service

1. Ajouter le service dans `docker-compose.yml`
2. Ajouter la cible dans `docker/prometheus/prometheus.yml`
3. Créer un dashboard Grafana si nécessaire

## Troubleshooting

### Les métriques n'apparaissent pas
```bash
# Vérifier que Prometheus scrape correctement
curl http://localhost:9090/api/v1/targets
```

### Grafana ne démarre pas
```bash
# Vérifier les permissions des volumes
docker-compose logs grafana
```

### MLflow erreur de connexion
```bash
# Vérifier que le service est bien démarré
docker-compose ps mlflow
docker-compose logs mlflow
```
