<template>
  <div class="home-view">
    <SearchBar />

    <CloudTypeFilter
      v-if="searchStore.cloudTypes.length > 0"
      :cloudTypes="searchStore.cloudTypes"
      :selectedTypes="searchStore.selectedTypes"
      @toggle="searchStore.toggleTypeAndSearch"
      @clear="searchStore.clearTypesAndSearch"
    />

    <!-- 搜索结果 -->
    <ResultList
      v-if="searchStore.keyword"
      :items="searchStore.results"
      :total="searchStore.total"
      :currentPage="searchStore.page"
      :totalPages="searchStore.totalPages"
      :loading="searchStore.loading"
      :error="searchStore.error"
      :searched="true"
      :sortBy="searchStore.sortBy"
      :searchTime="searchStore.searchTime"
      @update:page="onPageChange"
      @update:sortBy="onSortChange"
    />

    <!-- 初始状态（未搜索） -->
    <div v-else class="welcome-state">
      <div class="welcome-icon">🔍</div>
      <h2>网盘资源搜索神器</h2>
      <p>支持夸克网盘、百度网盘、阿里云盘、迅雷网盘等主流网盘</p>
      <p class="welcome-tip">输入关键字，聚合搜索互联网公开分享的网盘资源</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useSearchStore } from '../stores/search'
import SearchBar from '../components/SearchBar.vue'
import CloudTypeFilter from '../components/CloudTypeFilter.vue'
import ResultList from '../components/ResultList.vue'

const searchStore = useSearchStore()

onMounted(() => {
  searchStore.fetchCloudTypes()
  searchStore.fetchHotKeywords()
})

async function onPageChange(page: number) {
  searchStore.page = page
  await searchStore.doSearch(false)
}

async function onSortChange(sort: string) {
  searchStore.sortBy = sort
  searchStore.page = 1
  await searchStore.doSearch(true)
}
</script>

<style scoped>
.home-view {
  padding-top: var(--spacing-md);
}

.welcome-state {
  text-align: center;
  padding: var(--spacing-xl) 0;
  margin-top: var(--spacing-xl);
}

.welcome-icon {
  font-size: 4rem;
  margin-bottom: var(--spacing-lg);
}

.welcome-state h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--spacing-sm);
}

.welcome-state p {
  font-size: 0.95rem;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xs);
}

.welcome-tip {
  margin-top: var(--spacing-md);
  font-size: 0.85rem;
  color: var(--text-muted);
}
</style>
