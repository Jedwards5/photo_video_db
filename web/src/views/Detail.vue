<template>
  <div class="detail-wrap" v-if="media">
    <!-- Top bar -->
    <div class="topbar">
      <button class="back-btn" @click="$router.back()">←</button>
      <span class="topbar-date">{{ formatDate(media.timestamp) }}</span>
      <div class="nav-btns">
        <router-link v-if="media.prev_id" :to="`/media/${media.prev_id}`">‹</router-link>
        <router-link v-if="media.next_id" :to="`/media/${media.next_id}`">›</router-link>
      </div>
    </div>

    <!-- Media -->
    <div class="media-area">
      <video
        v-if="media.media_type === 'video'"
        controls
        playsinline
        class="media-el"
        :key="media.id"
      >
        <source :src="fileUrl" type="video/mp4" />
      </video>
      <img
        v-else
        :src="fileUrl"
        class="media-el"
        loading="lazy"
      />
    </div>

    <!-- Metadata -->
    <div class="meta-panel">
      <div v-if="media.location" class="meta-row">
        <span class="meta-label">📍</span>
        <span>{{ media.location }}</span>
      </div>

      <div v-if="media.people.length" class="meta-row">
        <span class="meta-label">👤</span>
        <span>{{ media.people.map(p => p.name).join(', ') }}</span>
      </div>

      <div v-if="media.tags.length" class="meta-row tags-row">
        <span class="meta-label">🏷️</span>
        <div class="tags">
          <span v-for="t in media.tags" :key="t.tag" class="tag">{{ t.tag }}</span>
        </div>
      </div>

      <div v-if="media.transcript" class="meta-row transcript-row">
        <span class="meta-label">💬</span>
        <p class="transcript">{{ media.transcript }}</p>
      </div>

      <div class="meta-row">
        <span class="meta-label">📁</span>
        <span class="filepath">{{ filename }}</span>
      </div>
    </div>
  </div>

  <div v-else-if="error" class="loading-msg">{{ error }}</div>
  <div v-else class="loading-msg">Loading…</div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const media = ref(null)
const error = ref('')

const fileUrl = computed(() => media.value ? api.fileUrl(media.value.id) : '')
const filename = computed(() => media.value?.filepath.split(/[\\/]/).pop() ?? '')

function formatDate(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleDateString('default', {
    weekday: 'short', year: 'numeric', month: 'long', day: 'numeric',
  })
}

async function load(id) {
  media.value = null
  error.value = ''
  try {
    media.value = await api.mediaDetail(id)
  } catch {
    error.value = 'Could not load media.'
  }
}

watch(() => route.params.id, (id) => load(id), { immediate: true })
</script>

<style scoped>
.detail-wrap { display: flex; flex-direction: column; min-height: 100dvh; background: #000; }

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: #111;
  position: sticky;
  top: 0;
  z-index: 10;
}
.back-btn { background: none; border: none; color: #fff; font-size: 1.2rem; cursor: pointer; padding: 0; }
.topbar-date { color: #aaa; font-size: 0.85rem; }
.nav-btns { display: flex; gap: 1rem; }
.nav-btns a { color: #fff; text-decoration: none; font-size: 1.4rem; line-height: 1; }

.media-area { display: flex; justify-content: center; background: #000; }
.media-el { max-width: 100%; max-height: 70dvh; object-fit: contain; }

.meta-panel { padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }
.meta-row { display: flex; gap: 0.6rem; align-items: flex-start; }
.meta-label { font-size: 1rem; flex-shrink: 0; padding-top: 1px; }
.meta-row span, .meta-row p { color: #ccc; font-size: 0.9rem; margin: 0; }

.tags { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.tag {
  padding: 0.2rem 0.6rem;
  border-radius: 20px;
  background: #222;
  color: #aaa;
  font-size: 0.8rem;
}
.transcript { line-height: 1.5; color: #aaa; }
.filepath { color: #555; font-size: 0.75rem; word-break: break-all; }

.loading-msg { text-align: center; color: #555; padding: 4rem; }
</style>
