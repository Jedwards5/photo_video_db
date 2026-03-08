<template>
  <div class="login-wrap">
    <div class="login-box">
      <h1>Memories</h1>
      <form @submit.prevent="submit">
        <input
          v-model="password"
          type="password"
          placeholder="Password"
          autocomplete="current-password"
          autofocus
        />
        <button type="submit" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>
        <p v-if="error" class="error">{{ error }}</p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const res = await api.login(password.value)
    localStorage.setItem('token', res.token)
    router.push('/')
  } catch {
    error.value = 'Incorrect password'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #111;
}
.login-box {
  width: 100%;
  max-width: 320px;
  padding: 2rem;
  text-align: center;
}
h1 {
  color: #fff;
  font-size: 1.8rem;
  margin-bottom: 2rem;
  letter-spacing: 0.05em;
}
input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #333;
  border-radius: 8px;
  background: #1a1a1a;
  color: #fff;
  font-size: 1rem;
  box-sizing: border-box;
  margin-bottom: 0.75rem;
}
button {
  width: 100%;
  padding: 0.75rem;
  border: none;
  border-radius: 8px;
  background: #fff;
  color: #111;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}
button:disabled { opacity: 0.6; }
.error { color: #f66; margin-top: 0.75rem; font-size: 0.9rem; }
</style>
