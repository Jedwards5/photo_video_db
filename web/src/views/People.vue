<template>
  <div>
    <nav class="topnav">
      <router-link to="/">Timeline</router-link>
      <router-link to="/people" class="active">People</router-link>
      <router-link to="/search">Search</router-link>
    </nav>

    <!-- Person list -->
    <div v-if="!selectedPerson">
      <div class="people-list">
        <div
          v-for="person in people"
          :key="person.id"
          class="person-card"
          @click="selectPerson(person)"
        >
          <div class="person-thumb-wrap">
            <img
              v-if="person.sample_id"
              :src="thumbnailUrl(person.sample_id)"
              class="person-thumb"
            />
            <div v-else class="person-thumb person-thumb-placeholder" />
          </div>
          <div class="person-info">
            <span class="person-name">{{ person.name }}</span>
            <span class="person-count">{{ person.count }} photos</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Person gallery -->
    <div v-else>
      <div class="gallery-header">
        <button class="back-btn" @click="selectedPerson = null">← Back</button>
        <h2>{{ selectedPerson.name }}</h2>
      </div>
      <div class="grid">
        <router-link
          v-for="item in personItems"
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
      <div ref="personSentinel" class="sentinel" />
      <p v-if="personLoading" class="loading-msg">Loading…</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { api } from '../api'

const people = ref([])
const selectedPerson = ref(null)
const personItems = ref([])
const personPage = ref(1)
const personDone = ref(false)
const personLoading = ref(false)
const personSentinel = ref(null)

const thumbnailUrl = (id) => api.thumbnailUrl(id)

onMounted(async () => {
  const res = await api.people()
  people.value = res
})

async function selectPerson(person) {
  selectedPerson.value = person
  personItems.value = []
  personPage.value = 1
  personDone.value = false
  await loadPersonPage()
}

async function loadPersonPage() {
  if (personLoading.value || personDone.value || !selectedPerson.value) return
  personLoading.value = true
  try {
    const res = await api.personMedia(selectedPerson.value.id, personPage.value)
    personItems.value.push(...res.items)
    if (personPage.value >= res.pages) personDone.value = true
    else personPage.value++
  } finally {
    personLoading.value = false
  }
}

let observer
watch(personSentinel, (el) => {
  observer?.disconnect()
  if (!el) return
  observer = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) loadPersonPage()
  }, { rootMargin: '200px' })
  observer.observe(el)
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

.people-list { padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }
.person-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 8px;
  background: #1a1a1a;
}
.person-card:active { background: #222; }
.person-thumb-wrap { width: 56px; height: 56px; border-radius: 50%; overflow: hidden; flex-shrink: 0; }
.person-thumb { width: 100%; height: 100%; object-fit: cover; }
.person-thumb-placeholder { background: #333; width: 100%; height: 100%; }
.person-info { display: flex; flex-direction: column; }
.person-name { color: #fff; font-size: 1rem; font-weight: 500; }
.person-count { color: #666; font-size: 0.85rem; }

.gallery-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: #111;
  position: sticky;
  top: 0;
  z-index: 10;
}
.back-btn {
  background: none;
  border: none;
  color: #fff;
  font-size: 0.95rem;
  cursor: pointer;
  padding: 0.25rem 0;
}
.gallery-header h2 { color: #fff; font-size: 1rem; font-weight: 600; margin: 0; }

.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; }
.thumb-wrap { position: relative; aspect-ratio: 1; overflow: hidden; background: #1a1a1a; display: block; }
.thumb { width: 100%; height: 100%; object-fit: cover; }
.thumb-placeholder { background: #222; }
.play-icon { position: absolute; bottom: 6px; right: 8px; font-size: 0.75rem; color: rgba(255,255,255,0.85); text-shadow: 0 1px 3px rgba(0,0,0,0.8); }
.sentinel { height: 1px; }
.loading-msg { text-align: center; color: #555; padding: 2rem; }
</style>
