<template>
  <div>
    <nav class="topnav">
      <router-link to="/">Timeline</router-link>
      <router-link to="/people">People</router-link>
      <router-link to="/search" class="active">Search</router-link>
    </nav>

    <div class="search-bar">
      <input
        v-model="query"
        type="search"
        placeholder="Search your memories…"
        @keyup.enter="doSearch"
        autofocus
      />
      <div class="mode-tabs">
        <button :class="{ active: mode === 'clip' }" @click="mode = 'clip'">Smart</button>
        <button :class="{ active: mode === 'tag' }" @click="mode = 'tag'">Tag</button>
        <button :class="{ active: mode === 'transcript' }" @click="mode = 'transcript'">Transcript</button>
      </div>
      <button class="search-btn" @click="doSearch" :disabled="!query.trim() || loading">Search</button>
    </div>

    <p v-if="loading" class="loading-msg">Searching…</p>

    <div v-else-if="results.length" class="grid">
      <router-link
        v-for="item in results"
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
        <div v-if="item.snippet" class="snippet">{{ item.snippet }}</div>
      </router-link>
    </div>

    <p v-else-if="searched" class="loading-msg">No results found.</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api'

const query = ref('')
const mode = ref('clip')
const results = ref([])
const loading = ref(false)
const searched = ref(false)

const thumbnailUrl = (id) => api.thumbnailUrl(id)

async function doSearch() {
  if (!query.value.trim()) return
  loading.value = true
  searched.value = false
  results.value = []
  try {
    const res = await api.search(query.value, mode.value)
    results.value = res.items
    searched.value = true
  } finally {
    loading.value = false
  }
}
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

.search-bar { padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }
input[type="search"] {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #333;
  border-radius: 8px;
  background: #1a1a1a;
  color: #fff;
  font-size: 1rem;
  box-sizing: border-box;
}
.mode-tabs { display: flex; gap: 0.5rem; }
.mode-tabs button {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #333;
  border-radius: 6px;
  background: #1a1a1a;
  color: #888;
  font-size: 0.85rem;
  cursor: pointer;
}
.mode-tabs button.active { background: #fff; color: #111; font-weight: 600; border-color: #fff; }
.search-btn {
  padding: 0.75rem;
  border: none;
  border-radius: 8px;
  background: #fff;
  color: #111;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}
.search-btn:disabled { opacity: 0.4; }

.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; }
.thumb-wrap { position: relative; aspect-ratio: 1; overflow: hidden; background: #1a1a1a; display: block; }
.thumb { width: 100%; height: 100%; object-fit: cover; }
.thumb-placeholder { background: #222; }
.play-icon { position: absolute; bottom: 6px; right: 8px; font-size: 0.75rem; color: rgba(255,255,255,0.85); text-shadow: 0 1px 3px rgba(0,0,0,0.8); }
.snippet {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0.3rem 0.4rem;
  font-size: 0.65rem;
  color: #fff;
  background: rgba(0,0,0,0.6);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.loading-msg { text-align: center; color: #555; padding: 2rem; }
</style>
