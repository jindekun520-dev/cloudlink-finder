import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { API_BASE } from '../api/base'

export interface SearchItem {
  title: string
  cloud_type: string
  cloud_name: string
  share_url: string
  share_code: string
  description: string
  file_size: string
  source_name: string
  validation_status: 'valid' | 'invalid' | 'locked' | 'unknown' | 'unchecked'
  validation_message: string
  verified_title: string
}

export interface CloudType {
  key: string
  name: string
}

export const useSearchStore = defineStore('search', () => {
  const keyword = ref('')
  const selectedTypes = ref<string[]>([])
  const sortBy = ref('relevance')
  const results = ref<SearchItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const totalPages = ref(0)
  const loading = ref(false)
  const error = ref('')
  const searchTime = ref(0)
  const cloudTypes = ref<CloudType[]>([])
  const hotKeywords = ref<{ keyword: string; count: number }[]>([])
  const history = ref<{ keyword: string }[]>([])
  let requestSerial = 0
  let activeController: AbortController | null = null

  const hasMore = computed(() => page.value < totalPages.value)

  async function fetchCloudTypes() {
    try {
      const res = await fetch(`${API_BASE}/sources/types`)
      const data = await res.json()
      if (data.code === 0) {
        cloudTypes.value = data.data
      }
    } catch {}
  }

  async function fetchHotKeywords() {
    try {
      const res = await fetch(`${API_BASE}/hot`)
      const data = await res.json()
      if (data.code === 0) {
        hotKeywords.value = data.data
      }
    } catch {}
  }

  async function fetchHistory() {
    try {
      const res = await fetch(`${API_BASE}/history`)
      const data = await res.json()
      if (data.code === 0) {
        history.value = data.data
      }
    } catch {}
  }

  async function doSearch(newSearch = false) {
    if (!keyword.value.trim()) return

    if (newSearch) {
      page.value = 1
    }

    const serial = ++requestSerial
    activeController?.abort()
    activeController = new AbortController()
    loading.value = true
    error.value = ''
    try {
      const params = new URLSearchParams()
      params.set('kw', keyword.value.trim())
      if (selectedTypes.value.length > 0) {
        params.set('types', selectedTypes.value.join(','))
      }
      params.set('page', String(page.value))
      params.set('size', String(pageSize.value))
      params.set('sort', sortBy.value)

      const res = await fetch(`${API_BASE}/search?${params.toString()}`, {
        signal: activeController.signal,
      })
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`)
      }

      if (data.code === 0) {
        results.value = data.data.items
        total.value = data.data.total
        totalPages.value = data.data.total_pages
        searchTime.value = data.data.search_time_ms || 0
      } else {
        error.value = data.message || '搜索失败，请稍后重试'
      }
    } catch (err) {
      if ((err as DOMException).name !== 'AbortError') {
        console.error('搜索失败:', err)
        error.value = err instanceof Error && err.message
          ? `搜索失败：${err.message}`
          : '搜索服务暂时不可用，请稍后重试'
      }
    } finally {
      if (serial === requestSerial) {
        loading.value = false
      }
    }
  }

  function toggleType(type: string) {
    const idx = selectedTypes.value.indexOf(type)
    if (idx > -1) {
      selectedTypes.value.splice(idx, 1)
    } else {
      selectedTypes.value.push(type)
    }
  }

  async function setKeyword(kw: string) {
    keyword.value = kw
    await doSearch(true)
  }

  async function toggleTypeAndSearch(type: string) {
    toggleType(type)
    if (keyword.value.trim()) {
      page.value = 1
      await doSearch(true)
    }
  }

  async function clearTypesAndSearch() {
    selectedTypes.value = []
    if (keyword.value.trim()) {
      page.value = 1
      await doSearch(true)
    }
  }

  return {
    keyword,
    selectedTypes,
    sortBy,
    results,
    total,
    page,
    pageSize,
    totalPages,
    loading,
    error,
    searchTime,
    cloudTypes,
    hotKeywords,
    history,
    hasMore,
    fetchCloudTypes,
    fetchHotKeywords,
    fetchHistory,
    doSearch,
    toggleType,
    toggleTypeAndSearch,
    clearTypesAndSearch,
    setKeyword,
  }
})
