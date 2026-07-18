<template>
  <div class="cloud-filter">
    <button
      v-for="ct in cloudTypes"
      :key="ct.key"
      class="filter-tag"
      :class="[ct.key, { active: selectedTypes.includes(ct.key) }]"
      @click="$emit('toggle', ct.key)"
    >
      {{ ct.name }}
    </button>

    <div v-if="selectedTypes.length > 0" class="filter-actions">
      <button class="clear-filter-btn" @click="$emit('clear')">
        清除筛选
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CloudType } from '../stores/search'

defineProps<{
  cloudTypes: CloudType[]
  selectedTypes: string[]
}>()

defineEmits<{
  toggle: [type: string]
  clear: []
}>()
</script>

<style scoped>
.cloud-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-md);
}

.filter-tag {
  padding: 5px 14px;
  border-radius: 20px;
  font-size: 0.82rem;
  font-weight: 500;
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 1.5px solid var(--border-color);
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.filter-tag:hover {
  border-color: var(--color-primary-light);
  color: var(--color-primary);
}

.filter-tag.active {
  color: #fff;
  border-color: transparent;
}

/* 各网盘激活颜色 */
.filter-tag.quark.active { background: var(--tag-quark); }
.filter-tag.baidu.active { background: var(--tag-baidu); }
.filter-tag.aliyun.active { background: var(--tag-aliyun); }
.filter-tag.xunlei.active { background: var(--tag-xunlei); }
.filter-tag.tianyi.active { background: var(--tag-tianyi); }
.filter-tag.uc.active { background: var(--tag-uc); }
.filter-tag.\31 15.active { background: var(--tag-115); }
.filter-tag.\31 23.active { background: var(--tag-123); }
.filter-tag.yidong.active { background: var(--tag-yidong); }

.filter-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.clear-filter-btn {
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 0.82rem;
  background: transparent;
  color: var(--color-primary);
  border: 1.5px solid var(--color-primary);
  transition: all var(--transition-fast);
}

.clear-filter-btn:hover {
  background: var(--color-primary);
  color: #fff;
}
</style>
