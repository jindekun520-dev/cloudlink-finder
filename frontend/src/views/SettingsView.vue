<template>
  <div class="settings-view">
    <h2 class="settings-title">⚙️ 设置</h2>

    <!-- 主题设置 -->
    <section class="settings-section">
      <h3>🎨 主题设置</h3>
      <div class="theme-options">
        <button
          v-for="opt in themeOptions"
          :key="opt.value"
          class="theme-option"
          :class="{ active: themeStore.mode === opt.value }"
          @click="themeStore.setMode(opt.value as ThemeMode)"
        >
          <span class="theme-icon">{{ opt.icon }}</span>
          <span>{{ opt.label }}</span>
        </button>
      </div>
    </section>

    <!-- 搜索源状态 -->
    <section class="settings-section">
      <h3>📡 搜索源状态</h3>
      <div class="source-list">
        <div v-for="s in sources" :key="s.name" class="source-item">
          <div class="source-info">
            <span class="source-name">{{ s.name }}</span>
            <span class="source-type">{{ s.type === 'search_engine' ? '搜索引擎' : 'API' }}</span>
          </div>
          <span class="source-status" :class="{ enabled: s.enabled }">
            {{ s.enabled ? '✓ 已启用' : '✗ 已禁用' }}
          </span>
        </div>
        <div v-if="sourceLoading" class="no-sources">
          加载搜索源信息中...
        </div>
        <div v-else-if="sourceError" class="no-sources source-error">
          {{ sourceError }}
        </div>
      </div>
    </section>

    <!-- 数据统计 -->
    <section class="settings-section">
      <h3>📊 搜索统计</h3>
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-value">{{ sources.length }}</span>
          <span class="stat-label">搜索源数量</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">9</span>
          <span class="stat-label">支持网盘类型</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">5分钟</span>
          <span class="stat-label">搜索缓存时长</span>
        </div>
      </div>
    </section>

    <!-- 关于 -->
    <section class="settings-section">
      <h3>ℹ️ 关于</h3>
      <div class="about-info">
        <p>网盘资源搜索神器 v1.0</p>
        <p>面向飞牛NAS的网盘资源聚合搜索引擎</p>
        <p>通过多源聚合（必应/搜狗等搜索引擎），实时检索互联网上的公开网盘分享链接</p>
        <p class="tech-stack">
          技术栈：Vue 3 + FastAPI + SQLite + Docker
        </p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useThemeStore, type ThemeMode } from '../stores/theme'

const themeStore = useThemeStore()

const themeOptions = [
  { value: 'auto', label: '跟随系统', icon: '🖥️' },
  { value: 'light', label: '亮色模式', icon: '☀️' },
  { value: 'dark', label: '暗色模式', icon: '🌙' },
]

interface SourceItem {
  name: string
  type: string
  enabled: boolean
}

const sources = ref<SourceItem[]>([])
const sourceLoading = ref(true)
const sourceError = ref('')

onMounted(async () => {
  try {
    const res = await fetch('/api/sources')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (data.code === 0) {
      sources.value = data.data
    } else {
      sourceError.value = '搜索源信息加载失败'
    }
  } catch {
    sourceError.value = '无法连接搜索服务，请稍后重试'
  } finally {
    sourceLoading.value = false
  }
})
</script>

<style scoped>
.settings-view {
  max-width: 700px;
  margin: 0 auto;
  padding-top: var(--spacing-md);
}

.settings-title {
  font-size: 1.4rem;
  font-weight: 700;
  margin-bottom: var(--spacing-lg);
}

.settings-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

.settings-section h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.theme-options {
  display: flex;
  gap: var(--spacing-sm);
}

.theme-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  border-radius: var(--border-radius);
  background: var(--bg-hover);
  color: var(--text-secondary);
  font-size: 0.85rem;
  border: 2px solid transparent;
  transition: all var(--transition-fast);
}

.theme-option:hover {
  border-color: var(--border-color);
}

.theme-option.active {
  border-color: var(--color-primary);
  background: rgba(99, 102, 241, 0.08);
  color: var(--color-primary);
}

.theme-icon {
  font-size: 1.5rem;
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.source-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--bg-hover);
  border-radius: var(--border-radius-sm);
}

.source-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.source-name {
  font-weight: 600;
  font-size: 0.9rem;
}

.source-type {
  font-size: 0.75rem;
  padding: 1px 8px;
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.1);
  color: var(--color-primary);
}

.source-status {
  font-size: 0.82rem;
  color: var(--text-muted);
}

.source-status.enabled {
  color: #22c55e;
}

.no-sources {
  color: var(--text-muted);
  text-align: center;
  padding: var(--spacing-md);
}

.source-error {
  color: #ef4444;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-md);
}

.stat-item {
  text-align: center;
  padding: var(--spacing-md);
  background: var(--bg-hover);
  border-radius: var(--border-radius-sm);
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-primary);
}

.stat-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 4px;
}

.about-info {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.8;
}

.tech-stack {
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--bg-hover);
  border-radius: var(--border-radius-sm);
  font-family: monospace;
  font-size: 0.82rem;
}

@media (max-width: 768px) {
  .theme-options {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
