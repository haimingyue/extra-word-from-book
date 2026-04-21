<template>
  <header class="app-nav surface-panel">
    <NuxtLink to="/" class="brand-lockup">
      <span class="brand-badge">L</span>
      <span class="brand-copy">
        <strong>Lexi</strong>
        <small>阅读前词汇分析</small>
      </span>
    </NuxtLink>

    <nav class="nav-links" aria-label="主导航">
      <NuxtLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-link"
        :class="{ 'nav-link-active': route.path === item.to }"
      >
        {{ item.label }}
      </NuxtLink>
    </nav>

    <div class="nav-actions">
      <button class="theme-switch" type="button" @click="toggleTheme">
        {{ theme === 'light' ? 'Dark' : 'Light' }}
      </button>
      <template v-if="isAuthenticated">
        <NuxtLink to="/profile" class="account-chip">
          {{ displayName }}
        </NuxtLink>
        <el-button round @click="handleLogout">退出</el-button>
      </template>
      <template v-else>
        <el-button round @click="openAuth('login')">登录</el-button>
        <el-button type="primary" round @click="openAuth('register')">注册</el-button>
      </template>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const { theme, toggleTheme } = useTheme()
const { isAuthenticated, displayName, openAuth, clearAuth } = useAuth()

const navItems = [
  { to: '/', label: '首页' },
  { to: '/history', label: '书架' },
  { to: '/vocabulary', label: '词库' },
  { to: '/vocab-test', label: '词汇量测试' }
]

const handleLogout = async () => {
  clearAuth()
  ElMessage.success('已退出登录')
  if (route.path !== '/') {
    await router.push('/')
  }
}
</script>

<style scoped>
.app-nav {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 20px;
  padding: 16px 20px;
}

.brand-lockup {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.brand-badge {
  display: inline-grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 16px;
  background: var(--surface-accent);
  color: var(--text-inverse);
  font-weight: 800;
  font-size: 20px;
  box-shadow: 0 12px 24px rgba(239, 90, 45, 0.22);
}

.brand-copy {
  display: grid;
  gap: 2px;
}

.brand-copy strong {
  font-size: 17px;
  line-height: 1;
}

.brand-copy small {
  color: var(--text-soft);
  font-size: 12px;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

.nav-link,
.account-chip,
.theme-switch {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid transparent;
  color: var(--text-main);
  background: transparent;
}

.nav-link-active,
.account-chip {
  background: var(--surface-soft);
  border-color: var(--border-soft);
}

.nav-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.theme-switch {
  background: var(--surface-soft);
  border-color: var(--border-soft);
}

@media (max-width: 980px) {
  .app-nav {
    grid-template-columns: 1fr;
    justify-items: stretch;
  }

  .nav-links {
    justify-content: flex-start;
  }

  .nav-actions {
    justify-content: flex-start;
  }
}
</style>
