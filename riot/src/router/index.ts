import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/draft',
      name: 'draft',
      component: () => import('../views/DraftView.vue'),
    },
    {
      path: '/joueur',
      name: 'joueur',
      component: () => import('../views/JoueurView.vue'),
    },
    {
      path: '/champions',
      name: 'champions',
      component: () => import('../views/ChampionsView.vue'),
    },
    {
      path: '/analyseur',
      name: 'analyseur',
      component: () => import('../views/AnalyzerView.vue')
    }
  ],
})

export default router
