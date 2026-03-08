import { createRouter, createWebHistory } from 'vue-router'
import Login from './views/Login.vue'
import Timeline from './views/Timeline.vue'
import People from './views/People.vue'
import Search from './views/Search.vue'
import Detail from './views/Detail.vue'

const routes = [
  { path: '/login', component: Login },
  { path: '/', component: Timeline, meta: { requiresAuth: true } },
  { path: '/people', component: People, meta: { requiresAuth: true } },
  { path: '/search', component: Search, meta: { requiresAuth: true } },
  { path: '/media/:id', component: Detail, meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) return '/login'
})

export default router
