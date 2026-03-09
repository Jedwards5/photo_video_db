<template>
  <div>
    <nav class="topnav">
      <router-link to="/" class="active">Timeline</router-link>
      <router-link to="/people">People</router-link>
      <router-link to="/search">Search</router-link>
    </nav>

    <div v-for="group in groups" :key="group.label" class="month-group">
      <h2 class="month-label">{{ group.label }}</h2>
      <div class="grid">
        <router-link
          v-for="item in group.items"
          :key="item.id"
          :to="`/media/${item.id}`"
          class="thumb-wrap"
        >
          <img
            v-if="item.has_thumbnail"
            :src="thumbnailUrl(item.id)"
            loading="lazy"
            class="thumb"
          />
          <div v-else class="thumb thumb-placeholder" />
          <span v-if="item.media_type === 'video'" class="play-icon">▶</span>
        </router-link>
      </div>
    </div>

    <div ref="sentinel" class="sentinel" />
    <p v-if="loading" class="loading-msg">Loading…</p>
    <p v-if="done && groups.length === 0" class="loading-msg">No media found.</p>
  </div>
</template>

<script>
export default { name: 'Timeline' }
</script>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'
import { api } from '../api'

const items = ref([])
const page = ref(1)
const totalPages = ref(1)
const loading = ref(false)
const done = ref(false)
const sentinel = ref(null)

const thumbnailUrl = (id) => api.thumbnailUrl(id)

const groups = computed(() => {
  const map = new Map()
  for (const item of items.value) {
    const label = item.timestamp
      ? new Date(item.timestamp).toLocaleString('default', { month: 'long', year: 'numeric' })
      : 'Unknown date'
    if (!map.has(label)) map.set(label, [])
    map.get(label).push(item)
  }
  return [...map.entries()].map(([label, items]) => ({ label, items }))
})

async function loadPage() {
  if (loading.value || done.value) return
  loading.value = true
  try {
    const res = await api.timeline(page.value)
    items.value.push(...res.items)
    totalPages.value = res.pages
    if (page.value >= res.pages) done.value = true
    else page.value++
  } finally {
    loading.value = false
  }
}

let savedScroll = 0
onDeactivated(() => { savedScroll = window.scrollY })
onActivated(() => { window.scrollTo(0, savedScroll) })

let observer
onMounted(() => {
  loadPage()
  observer = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) loadPage()
  }, { rootMargin: '200px' })
  if (sentinel.value) observer.observe(sentinel.value)
})
onUnmounted(() => observer?.disconnect())
</script>

<style scoped>
.topnav {
  display: flex;
  gap: 1.5rem;
  padding: 1rem;
  background: #111;
  position: sticky;
  top: 0;
  z-index: 10;
}
.topnav a { color: #888; text-decoration: none; font-size: 0.95rem; }
.topnav a.active, .topnav a.router-link-active { color: #fff; font-weight: 600; }

.month-label {
  padding: 0.75rem 1rem 0.25rem;
  font-size: 0.9rem;
  color: #888;
  font-weight: 500;
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2px;
}
.thumb-wrap {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
  background: #1a1a1a;
  display: block;
}
.thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-placeholder { background: #222; }
.play-icon {
  position: absolute;
  bottom: 6px;
  right: 8px;
  font-size: 0.75rem;
  color: rgba(255,255,255,0.85);
  text-shadow: 0 1px 3px rgba(0,0,0,0.8);
}
.sentinel { height: 1px; }
.loading-msg { text-align: center; color: #555; padding: 2rem; }
</style>
