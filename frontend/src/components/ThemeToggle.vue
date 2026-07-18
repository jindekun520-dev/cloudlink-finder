<template>
  <button class="theme-toggle" @click="theme.toggle()" :title="theme.mode === 'dark' ? '切换亮色模式' : '切换暗色模式'">
    <span v-if="theme.mode === 'dark' || (theme.mode === 'auto' && isDark)">☀️</span>
    <span v-else>🌙</span>
  </button>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useThemeStore } from '../stores/theme'

const theme = useThemeStore()
const isDark = ref(false)

onMounted(() => {
  isDark.value = document.documentElement.getAttribute('data-theme') === 'dark'
  const observer = new MutationObserver(() => {
    isDark.value = document.documentElement.getAttribute('data-theme') === 'dark'
  })
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
})
</script>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--bg-hover);
  font-size: 1.1rem;
  transition: background var(--transition-fast);
}

.theme-toggle:hover {
  background: var(--border-color);
}
</style>
