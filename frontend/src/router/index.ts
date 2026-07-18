import { createRouter, createWebHistory } from 'vue-router'

const GATEWAY_PREFIX = '/app/third-pan-search'
const isGatewayPath = window.location.pathname === GATEWAY_PREFIX
  || window.location.pathname.startsWith(`${GATEWAY_PREFIX}/`)

const router = createRouter({
  history: createWebHistory(isGatewayPath ? `${GATEWAY_PREFIX}/` : '/'),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
    },
  ],
})

export default router
