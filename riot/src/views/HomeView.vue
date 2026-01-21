<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="home">
    <div class="hero">
      <h1>🎮 Riot Stats</h1>
      <p>Analysez vos parties, suivez vos joueurs et découvrez les meilleurs champions</p>
    </div>

    <div class="stats-preview">
      <div class="stat-card">
        <h3>📊 Drafts</h3>
        <p>Consultez les compositions d'équipe</p>
        <RouterLink to="/draft" class="btn">Voir les Drafts</RouterLink>
      </div>

      <div class="stat-card">
        <h3>🔍 Joueurs</h3>
        <p>Recherchez un joueur et son historique</p>
        <RouterLink to="/joueur" class="btn">Rechercher</RouterLink>
      </div>

      <div class="stat-card">
        <h3>🏆 Champions</h3>
        <p>Win rates par poste</p>
        <RouterLink to="/champions" class="btn">Statistiques</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  text-align: center;
}

.hero {
  padding: 3rem 1rem;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 12px;
  margin-bottom: 2rem;
}

.hero h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  color: #42b883;
}

.hero p {
  color: #888;
  font-size: 1.1rem;
}

.stats-preview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  background: #1a1a2e;
  padding: 2rem;
  border-radius: 12px;
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-5px);
}

.stat-card h3 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
  color: white;
}

.stat-card p {
  color: #888;
  margin-bottom: 1rem;
}

.btn {
  display: inline-block;
  background: #42b883;
  color: #1a1a2e;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  transition: background 0.2s;
}

.btn:hover {
  background: #3aa876;
}
</style>
