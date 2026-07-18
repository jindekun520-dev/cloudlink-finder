import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ThemeMode = 'auto' | 'dark' | 'light'

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(
    (localStorage.getItem('pan-search-theme') as ThemeMode) || 'auto'
  )

  function applyTheme() {
    const isDark =
      mode.value === 'dark' ||
      (mode.value === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)

    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
    localStorage.setItem('pan-search-theme', mode.value)
  }

  function setMode(newMode: ThemeMode) {
    mode.value = newMode
    applyTheme()
  }

  function toggle() {
    const current = document.documentElement.getAttribute('data-theme')
    mode.value = current === 'dark' ? 'light' : 'dark'
    applyTheme()
  }

  // 初始应用
  applyTheme()

  // 监听系统主题变化
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (mode.value === 'auto') applyTheme()
  })

  return { mode, setMode, toggle, applyTheme }
})
