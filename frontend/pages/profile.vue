<template>
  <div class="profile-page">
    <header class="page-topbar">
      <div class="topbar-left">
        <NuxtLink to="/" class="back-link soft-pill">返回首页</NuxtLink>
        <NuxtLink to="/vocabulary" class="back-link soft-pill">词库</NuxtLink>
        <NuxtLink to="/history" class="back-link soft-pill">书架</NuxtLink>
        <button class="theme-toggle soft-pill" type="button" @click="toggleTheme">
          <span>{{ theme === 'light' ? '浅色' : '暗色' }}</span>
        </button>
      </div>

      <div class="topbar-right">
        <template v-if="isAuthenticated">
          <div class="user-chip soft-pill">
            <span>{{ displayName }}</span>
          </div>
          <el-button round @click="handleLogout">退出</el-button>
        </template>
        <template v-else>
          <el-button round @click="openAuth('login')">登录</el-button>
          <el-button type="primary" round @click="openAuth('register')">注册</el-button>
        </template>
      </div>
    </header>

    <section class="hero-panel soft-panel">
      <div class="hero-copy">
        <span class="hero-kicker soft-pill">Profile</span>
        <h1>我的</h1>
        <p>配置默认词汇基础。后续首页分析、书架重新分析等入口会自动使用这里保存的默认值。</p>
      </div>
      <div class="hero-meta">
        <div class="meta-card">
          <strong>{{ displayName }}</strong>
          <span>当前账号</span>
        </div>
        <div class="meta-card">
          <strong>{{ currentKnownWordsLabel }}</strong>
          <span>默认词汇基础</span>
        </div>
      </div>
    </section>

    <section v-if="!isAuthenticated" class="empty-panel soft-panel">
      <h2>登录后管理你的默认设置</h2>
      <p>登录后可保存默认词汇基础，下次分析时自动带入。</p>
      <div class="empty-actions">
        <el-button type="primary" round @click="openAuth('login')">立即登录</el-button>
        <NuxtLink to="/">
          <el-button round>回到首页</el-button>
        </NuxtLink>
      </div>
    </section>

    <section v-else class="settings-panel soft-panel">
      <div class="panel-head">
        <div>
          <span class="section-label">Default Level</span>
          <h2>默认词汇基础</h2>
        </div>
        <p>支持 COCA 数值档位，也补充了初中、高中、四级、六级几个常用标签。</p>
      </div>

      <div class="setting-grid">
        <div class="setting-card soft-panel">
          <span class="field-label">默认选项</span>
          <el-select v-model="selectedLevel" size="large" class="level-select">
            <el-option
              v-for="option in knownWordsOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </div>

        <div class="setting-card soft-panel preview-card">
          <span class="field-label">当前预览</span>
          <strong>{{ selectedKnownWordsLabel }}</strong>
          <p>保存后，首页和书架中的默认档位会同步更新。</p>
        </div>
      </div>

      <div class="panel-actions">
        <el-button round @click="resetLevel">恢复默认</el-button>
        <el-button type="primary" round @click="saveLevel">保存设置</el-button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

const router = useRouter()
const { theme, toggleTheme } = useTheme()
const { isAuthenticated, displayName, openAuth, clearAuth } = useAuth()
const { knownWordsOptions, getKnownWordsLabel } = useKnownWordsOptions()
const { defaultKnownWordsLevel, setDefaultKnownWordsLevel } = useUserPreferences()

const selectedLevel = ref(defaultKnownWordsLevel.value)

const selectedKnownWordsLabel = computed(() => getKnownWordsLabel(selectedLevel.value))
const currentKnownWordsLabel = computed(() => getKnownWordsLabel(defaultKnownWordsLevel.value))

watch(
  () => defaultKnownWordsLevel.value,
  (value) => {
    selectedLevel.value = value
  },
  { immediate: true }
)

const resetLevel = () => {
  selectedLevel.value = 3000
}

const saveLevel = () => {
  setDefaultKnownWordsLevel(selectedLevel.value)
  ElMessage.success(`默认词汇基础已保存为 ${getKnownWordsLabel(selectedLevel.value)}`)
}

const handleLogout = async () => {
  clearAuth()
  ElMessage.success('已退出登录')
  await router.push('/')
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  width: min(1180px, 100%);
  margin: 0 auto;
  padding: 24px 20px 48px;
}

.page-topbar,
.topbar-left,
.topbar-right,
.hero-panel,
.hero-meta,
.setting-grid,
.panel-actions,
.empty-actions {
  display: flex;
  align-items: center;
}

.page-topbar,
.hero-panel {
  justify-content: space-between;
}

.topbar-left,
.topbar-right,
.hero-meta,
.panel-actions,
.empty-actions {
  gap: 12px;
}

.back-link,
.theme-toggle,
.user-chip {
  padding: 12px 18px;
  color: var(--text-main);
  border: 0;
}

.hero-panel,
.settings-panel,
.empty-panel {
  margin-top: 24px;
  padding: 28px;
}

.hero-panel {
  gap: 20px;
}

.hero-copy {
  max-width: 720px;
}

.hero-kicker,
.section-label {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 10px 16px;
  color: var(--primary-600);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.hero-copy h1,
.panel-head h2,
.empty-panel h2 {
  margin: 18px 0 12px;
  font-size: clamp(40px, 5vw, 62px);
  line-height: 0.96;
  letter-spacing: -0.05em;
}

.hero-copy p,
.panel-head p,
.empty-panel p,
.preview-card p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.8;
}

.hero-meta {
  align-items: stretch;
  flex-wrap: wrap;
}

.meta-card,
.setting-card {
  display: grid;
  gap: 8px;
  min-width: 180px;
  padding: 18px 20px;
  border-radius: var(--radius-sm);
  background: var(--surface-3);
  box-shadow: var(--shadow-inset);
}

.meta-card strong,
.preview-card strong {
  font-size: 26px;
}

.meta-card span,
.field-label {
  color: var(--text-soft);
}

.settings-panel {
  display: grid;
  gap: 22px;
}

.panel-head {
  display: grid;
  gap: 10px;
}

.setting-grid {
  gap: 18px;
  align-items: stretch;
}

.setting-card {
  flex: 1;
}

.preview-card {
  justify-content: center;
}

.level-select {
  width: 100%;
}

.panel-actions {
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .page-topbar,
  .hero-panel,
  .setting-grid,
  .panel-actions {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 720px) {
  .profile-page {
    padding-inline: 14px;
  }

  .topbar-left,
  .topbar-right,
  .hero-meta,
  .empty-actions {
    flex-wrap: wrap;
  }

  .hero-panel,
  .settings-panel,
  .empty-panel {
    padding: 20px;
  }

  .hero-copy h1,
  .panel-head h2,
  .empty-panel h2 {
    font-size: 36px;
  }
}
</style>
