<template>
  <div class="search-bar">
    <div class="search-input-wrapper">
      <span class="search-icon">🔍</span>
      <input
        ref="inputRef"
        v-model="localKeyword"
        type="text"
        class="search-input"
        placeholder="输入关键字搜索网盘资源..."
        @keydown.enter="handleSearch"
        @focus="showHistory = true"
      />
      <button v-if="localKeyword" class="clear-btn" @click="clearInput">✕</button>
      <button class="search-btn" @click="handleSearch" :disabled="!localKeyword.trim()">
        搜索
      </button>
    </div>

    <!-- 搜索历史/热门推荐下拉 -->
    <div v-if="showHistory && !localKeyword" class="search-dropdown">
      <div v-if="history.length > 0" class="dropdown-section">
        <div class="section-header">
          <span>📜 搜索历史</span>
          <button class="section-action" @click="clearHistory">清空</button>
        </div>
        <div class="keyword-tags">
          <button
            v-for="h in history.slice(0, 10)"
            :key="h.keyword"
            class="keyword-tag"
            @click="quickSearch(h.keyword)"
          >
            {{ h.keyword }}
          </button>
        </div>
      </div>
      <div v-if="hotKeywords.length > 0" class="dropdown-section">
        <div class="section-header">
          <span>🔥 热门搜索</span>
        </div>
        <div class="keyword-tags">
          <button
            v-for="h in hotKeywords"
            :key="h.keyword"
            class="keyword-tag hot"
            @click="quickSearch(h.keyword)"
          >
            {{ h.keyword }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useSearchStore } from '../stores/search'
import { searchAPI } from '../api/search'

const searchStore = useSearchStore()

const localKeyword = ref(searchStore.keyword)
const showHistory = ref(false)
const inputRef = ref<HTMLInputElement>()
const history = ref<{ keyword: string }[]>([])
const hotKeywords = ref<{ keyword: string; count: number }[]>([])

async function refreshSuggestions() {
  try {
    const [hRes, hotRes] = await Promise.all([
      searchAPI.getHistory(),
      searchAPI.getHot(),
    ])
    if (hRes.code === 0) history.value = hRes.data
    if (hotRes.code === 0) hotKeywords.value = hotRes.data
  } catch {
    // 搜索建议属于增强功能，失败时不影响主搜索流程。
  }
}

function handleDocumentClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.search-bar')) {
    showHistory.value = false
  }
}

onMounted(async () => {
  document.addEventListener('click', handleDocumentClick)
  await refreshSuggestions()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})

async function handleSearch() {
  const kw = localKeyword.value.trim()
  if (!kw) return
  showHistory.value = false
  await searchStore.setKeyword(kw)
  await refreshSuggestions()
}

async function quickSearch(kw: string) {
  localKeyword.value = kw
  showHistory.value = false
  await searchStore.setKeyword(kw)
  await refreshSuggestions()
}

function clearInput() {
  localKeyword.value = ''
  showHistory.value = true
  inputRef.value?.focus()
}

async function clearHistory() {
  const result = await searchAPI.clearHistory()
  if (result.code === 0) history.value = []
}
</script>

<style scoped>
.search-bar {
  position: relative;
  margin-bottom: var(--spacing-lg);
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  background: var(--bg-card);
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 4px 4px 4px 16px;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.search-input-wrapper:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

.search-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  height: 44px;
  border: none;
  background: transparent;
  font-size: 1rem;
  color: var(--text-primary);
}

.search-input::placeholder {
  color: var(--text-muted);
}

.clear-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--bg-hover);
  color: var(--text-secondary);
  font-size: 0.8rem;
  flex-shrink: 0;
}

.search-btn {
  padding: 10px 24px;
  border-radius: var(--border-radius-sm);
  background: var(--color-primary);
  color: var(--text-inverse);
  font-size: 0.95rem;
  font-weight: 600;
  transition: background var(--transition-fast);
  flex-shrink: 0;
}

.search-btn:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.search-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 下拉面板 */
.search-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-lg);
  padding: var(--spacing-md);
  z-index: 50;
  max-height: 320px;
  overflow-y: auto;
}

.dropdown-section {
  margin-bottom: var(--spacing-md);
}

.dropdown-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-sm);
}

.section-action {
  background: none;
  color: var(--color-primary);
  font-size: 0.8rem;
}

.keyword-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.keyword-tag {
  padding: 4px 12px;
  border-radius: 16px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  font-size: 0.85rem;
  transition: all var(--transition-fast);
}

.keyword-tag:hover {
  background: var(--color-primary-light);
  color: var(--text-inverse);
}

.keyword-tag.hot {
  background: rgba(249, 115, 22, 0.1);
  color: #f97316;
}

@media (max-width: 768px) {
  .search-input-wrapper {
    padding: 2px 2px 2px 12px;
  }

  .search-input {
    height: 40px;
    font-size: 0.95rem;
  }

  .search-btn {
    padding: 8px 16px;
    font-size: 0.85rem;
  }
}
</style>
