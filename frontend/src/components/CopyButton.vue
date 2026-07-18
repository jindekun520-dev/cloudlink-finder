<template>
  <a
    v-if="openUrl"
    class="copy-btn"
    :href="openUrl"
    target="_blank"
    rel="noopener noreferrer"
    title="复制并打开网盘页面"
    @click="doCopy"
    :class="{ copied: status === 'copied', failed: status === 'failed' }"
  >
    <span v-if="status === 'idle'">{{ label }}</span>
    <span v-else-if="status === 'copied'">✓ 已复制并打开</span>
    <span v-else>复制失败</span>
  </a>
  <button
    v-else
    class="copy-btn"
    :title="label"
    @click="doCopy"
    :class="{ copied: status === 'copied', failed: status === 'failed' }"
  >
    <span v-if="status === 'idle'">{{ label }}</span>
    <span v-else-if="status === 'copied'">✓ 已复制</span>
    <span v-else>复制失败</span>
  </button>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { copyText } from '../utils/clipboard'

const props = defineProps<{
  text: string
  label?: string
  openUrl?: string
}>()

const status = ref<'idle' | 'copied' | 'failed'>('idle')

async function doCopy() {
  status.value = await copyText(props.text) ? 'copied' : 'failed'
  setTimeout(() => {
    status.value = 'idle'
  }, 1500)
}
</script>

<style scoped>
.copy-btn {
  padding: 5px 12px;
  border-radius: var(--border-radius-sm);
  font-size: 0.8rem;
  background: var(--bg-hover);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  white-space: nowrap;
  flex-shrink: 0;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.copy-btn:hover {
  background: var(--color-primary-light);
  color: #fff;
}

.copy-btn.copied {
  background: #22c55e;
  color: #fff;
}

.copy-btn.failed {
  background: #ef4444;
  color: #fff;
}
</style>
