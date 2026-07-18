<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-left">
        <span class="app-logo">🔍</span>
        <h1 class="app-title">网盘资源搜索</h1>
      </div>
      <div class="header-right">
        <router-link to="/" class="nav-link" active-class="active">搜索</router-link>
        <router-link to="/settings" class="nav-link" active-class="active">设置</router-link>
        <ThemeToggle />
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
    <footer class="app-footer">
      <span>网盘资源搜索神器 v1.0 · 支持夸克/百度/阿里/迅雷等主流网盘</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import ThemeToggle from './components/ThemeToggle.vue'
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: 100;
  transition: background var(--transition-normal);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.app-logo {
  font-size: 1.5rem;
}

.app-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.nav-link {
  padding: 6px 14px;
  border-radius: var(--border-radius-sm);
  font-size: 0.9rem;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  text-decoration: none;
}

.nav-link:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-link.active {
  background: var(--color-primary);
  color: var(--text-inverse);
}

.app-main {
  flex: 1;
  padding: var(--spacing-lg);
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
}

.app-footer {
  text-align: center;
  padding: var(--spacing-md);
  color: var(--text-muted);
  font-size: 0.8rem;
  border-top: 1px solid var(--border-color);
}

@media (max-width: 768px) {
  .app-header {
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .app-title {
    font-size: 1rem;
  }

  .app-main {
    padding: var(--spacing-md);
  }
}
</style>
