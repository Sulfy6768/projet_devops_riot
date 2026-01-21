<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header>
    <div class="header-content">
      <RouterLink to="/" class="logo">🎮 Riot Stats</RouterLink>
      <nav>
        <RouterLink to="/">Accueil</RouterLink>
        <RouterLink to="/draft">Draft</RouterLink>
        <RouterLink to="/joueur">Joueur</RouterLink>
        <RouterLink to="/champions">Champions</RouterLink>
      </nav>
    </div>
  </header>

  <main>
    <RouterView />
  </main>
</template>

<style scoped>
header {
  background-color: #1a1a2e;
  padding: 0.5rem 1rem;
  color: white;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  max-width: 1200px;
  margin: 0 auto;
  gap: 0.4rem;
}

.logo {
  font-size: 1.2rem;
  font-weight: 700;
  color: #42b883;
  text-decoration: none;
}

nav {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
}

nav a {
  color: #a0aec0;
  text-decoration: none;
  font-weight: 500;
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  transition: all 0.2s;
}

nav a:hover {
  color: white;
  background: #2d3748;
}

nav a.router-link-active {
  color: #42b883;
  background: rgba(66, 184, 131, 0.1);
}

main {
  padding: 1rem;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
}
</style>
