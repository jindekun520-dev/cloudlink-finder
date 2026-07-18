<template>
  <div class="result-list">
    <!-- 搜索结果统计 -->
    <div v-if="total > 0" class="result-header">
      <span>
        共找到 <strong>{{ total }}</strong> 条结果
        <span v-if="searchTime > 0" class="search-time">（{{ searchTime }}ms）</span>
      </span>
      <div class="sort-options">
        <button
          class="sort-btn"
          :class="{ active: sortBy === 'relevance' }"
          @click="$emit('update:sortBy', 'relevance')"
        >
          综合
        </button>
        <button
          class="sort-btn"
          :class="{ active: sortBy === 'recent' }"
          @click="$emit('update:sortBy', 'recent')"
        >
          最新
        </button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>正在搜索中...</p>
    </div>

    <div v-else-if="error" class="empty-state error-state">
      <div class="empty-icon">⚠️</div>
      <h3>搜索失败</h3>
      <p>{{ error }}</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="total === 0 && searched" class="empty-state">
      <div class="empty-icon">🔍</div>
      <h3>暂无搜索结果</h3>
      <p>请尝试更换关键字或放宽筛选条件</p>
    </div>

    <!-- 结果列表 -->
    <div v-else class="results-grid">
      <ResultCard v-for="item in items" :key="item.share_url" :item="item" />
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="pagination">
      <button
        class="page-btn"
        :disabled="currentPage <= 1"
        @click="$emit('update:page', currentPage - 1)"
      >
        上一页
      </button>

      <template v-for="p in displayPages" :key="p">
        <button
          v-if="p !== '...'"
          class="page-btn"
          :class="{ active: p === currentPage }"
          @click="$emit('update:page', p as number)"
        >
          {{ p }}
        </button>
        <span v-else class="page-ellipsis">...</span>
      </template>

      <button
        class="page-btn"
        :disabled="currentPage >= totalPages"
        @click="$emit('update:page', currentPage + 1)"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SearchItem } from '../stores/search'
import ResultCard from './ResultCard.vue'

const props = defineProps<{
  items: SearchItem[]
  total: number
  currentPage: number
  totalPages: number
  loading: boolean
  error: string
  searched: boolean
  sortBy: string
  searchTime: number
}>()

defineEmits<{
  'update:page': [page: number]
  'update:sortBy': [sort: string]
}>()

const displayPages = computed(() => {
  const pages: (number | string)[] = []
  const tp = props.totalPages
  const cp = props.currentPage

  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
    return pages
  }

  pages.push(1)
  if (cp > 3) pages.push('...')

  const start = Math.max(2, cp - 1)
  const end = Math.min(tp - 1, cp + 1)
  for (let i = start; i <= end; i++) pages.push(i)

  if (cp < tp - 2) pages.push('...')
  pages.push(tp)

  return pages
})
</script>

<style scoped>
.result-list {
  min-height: 200px;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.result-header strong {
  color: var(--color-primary);
}

.search-time {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.sort-options {
  display: flex;
  gap: var(--spacing-xs);
}

.sort-btn {
  padding: 4px 12px;
  border-radius: var(--border-radius-sm);
  font-size: 0.82rem;
  background: transparent;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.sort-btn.active {
  background: var(--color-primary);
  color: #fff;
}

.sort-btn:hover:not(.active) {
  background: var(--bg-hover);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl) 0;
  color: var(--text-secondary);
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border-color);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: var(--spacing-md);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl) 0;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: var(--spacing-md);
}

.empty-state h3 {
  font-size: 1.1rem;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.empty-state p {
  font-size: 0.9rem;
}

.results-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-lg);
  flex-wrap: wrap;
}

.page-btn {
  min-width: 36px;
  height: 36px;
  padding: 0 8px;
  border-radius: var(--border-radius-sm);
  font-size: 0.85rem;
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  transition: all var(--transition-fast);
}

.page-btn:hover:not(:disabled):not(.active) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.page-btn.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-ellipsis {
  color: var(--text-muted);
  padding: 0 4px;
}
</style>
