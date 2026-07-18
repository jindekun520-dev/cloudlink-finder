<template>
  <div class="result-card">
    <div class="card-header">
      <span class="cloud-badge" :class="item.cloud_type">
        {{ item.cloud_name }}
      </span>
      <span
        v-if="item.validation_status === 'valid'"
        class="validity-badge"
        :title="item.validation_message"
      >
        ✓ 链接有效
      </span>
      <span v-if="item.file_size" class="file-size">{{ item.file_size }}</span>
    </div>

    <h3 class="card-title">{{ item.title }}</h3>

    <p v-if="item.verified_title" class="verified-title">
      网盘实际内容：{{ item.verified_title }}
    </p>

    <p v-if="item.description" class="card-desc">{{ item.description }}</p>

    <div class="card-link">
      <code class="link-text">{{ item.share_url }}</code>
      <CopyButton :text="item.share_url" label="复制链接" :openUrl="item.share_url" />
    </div>

    <div v-if="item.share_code" class="card-code">
      <span class="code-label">提取码：</span>
      <code class="code-value">{{ item.share_code }}</code>
      <CopyButton :text="item.share_code" label="复制提取码" />
    </div>

    <div class="card-footer">
      <a
        class="copy-all-btn"
        :class="copyAllStatus"
        :href="item.share_url"
        target="_blank"
        rel="noopener noreferrer"
        title="复制链接及提取码并打开网盘页面"
        @click="copyAll"
      >
        {{ copyAllLabel }}
      </a>
      <span class="source-tag">来自 {{ item.source_name }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SearchItem } from '../stores/search'
import CopyButton from './CopyButton.vue'
import { copyText } from '../utils/clipboard'

const props = defineProps<{
  item: SearchItem
}>()
const copyAllStatus = ref<'idle' | 'copied' | 'failed'>('idle')
const copyAllLabel = computed(() => {
  if (copyAllStatus.value === 'copied') return '✓ 已复制并打开网盘'
  if (copyAllStatus.value === 'failed') return '复制失败，请手动复制'
  return '📋 复制链接及提取码'
})

async function copyAll() {
  let text = props.item.share_url
  if (props.item.share_code) {
    text += `\n提取码: ${props.item.share_code}`
  }
  copyAllStatus.value = await copyText(text) ? 'copied' : 'failed'
  window.setTimeout(() => {
    copyAllStatus.value = 'idle'
  }, 1500)
}
</script>

<style scoped>
.result-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-md);
  transition: box-shadow var(--transition-fast), transform var(--transition-fast);
}

.result-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.cloud-badge {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #fff;
}

.cloud-badge.quark { background: var(--tag-quark); }
.cloud-badge.baidu { background: var(--tag-baidu); }
.cloud-badge.aliyun { background: var(--tag-aliyun); }
.cloud-badge.xunlei { background: var(--tag-xunlei); }
.cloud-badge.tianyi { background: var(--tag-tianyi); }
.cloud-badge.uc { background: var(--tag-uc); }
.cloud-badge.\31 15 { background: var(--tag-115); }
.cloud-badge.\31 23 { background: var(--tag-123); }
.cloud-badge.yidong { background: var(--tag-yidong); }

.file-size {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.validity-badge {
  padding: 2px 9px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #15803d;
  background: rgba(34, 197, 94, 0.14);
  border: 1px solid rgba(34, 197, 94, 0.28);
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
  line-height: 1.4;
  word-break: break-all;
}

.card-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-sm);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.verified-title {
  margin: -2px 0 var(--spacing-sm);
  font-size: 0.8rem;
  line-height: 1.45;
  color: #16a34a;
  word-break: break-word;
}

.card-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.link-text {
  flex: 1;
  padding: 6px 10px;
  background: var(--bg-input);
  border-radius: var(--border-radius-sm);
  font-size: 0.82rem;
  color: var(--color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-code {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.code-label {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.code-value {
  padding: 2px 8px;
  background: rgba(99, 102, 241, 0.1);
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-primary);
  letter-spacing: 2px;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
}

.copy-all-btn {
  font-size: 0.82rem;
  color: var(--color-primary);
  cursor: pointer;
  background: transparent;
  padding: 0;
  transition: opacity var(--transition-fast);
  text-decoration: none;
}

.copy-all-btn:hover {
  opacity: 0.8;
}

.copy-all-btn.copied {
  color: #22c55e;
}

.copy-all-btn.failed {
  color: #ef4444;
}

.source-tag {
  font-size: 0.75rem;
  color: var(--text-muted);
}
</style>
