<template>
  <div class="app-shell section-stack profile-page">
    <AppNavigation />

    <section class="settings-layout">
      <article class="surface-panel page-card settings-intro">
        <span class="eyebrow">Profile</span>
        <div class="section-heading">
          <h1>默认词汇基础</h1>
          <p>保存后，首页分析、书架重新分析等入口都会自动带入这个默认范围。</p>
        </div>

        <div class="intro-stats">
          <article class="intro-stat">
            <span>当前账号</span>
            <strong>{{ displayName }}</strong>
          </article>
          <article class="intro-stat">
            <span>默认范围</span>
            <strong>{{ currentKnownWordsLabel }}</strong>
          </article>
        </div>
      </article>

      <EmptyStateCard
        v-if="!isAuthenticated"
        eyebrow="Sign In"
        title="登录后管理你的默认设置"
        description="登录后可保存默认词汇基础，下次分析时自动带入。"
      >
        <template #actions>
          <el-button type="primary" round @click="openAuth('login')">立即登录</el-button>
          <NuxtLink to="/">
            <el-button round>回到首页</el-button>
          </NuxtLink>
        </template>
      </EmptyStateCard>

      <article v-else class="surface-panel page-card settings-panel">
        <div class="section-heading compact-heading">
          <span class="eyebrow">Default Range</span>
          <h2>选择默认范围</h2>
          <p>同一个入口中支持考试标签和 COCA 档位，保存后会同步到首页和书架。</p>
        </div>

        <div class="setting-grid">
          <div class="setting-card">
            <span class="field-label">默认选项</span>
            <el-select v-model="selectedOptionKey" size="large" class="level-select">
              <el-option-group
                v-for="group in knownWordsOptionGroups"
                :key="group.label"
                :label="group.label"
              >
                <el-option
                  v-for="option in group.options"
                  :key="option.key"
                  :label="option.label"
                  :value="option.key"
                />
              </el-option-group>
            </el-select>
          </div>

          <div class="setting-card preview-card">
            <span class="field-label">当前预览</span>
            <strong>{{ selectedKnownWordsLabel }}</strong>
            <p>保存后，首页和书架中的默认范围会同步更新。</p>
          </div>
        </div>

        <div class="panel-actions">
          <el-button round @click="resetLevel">恢复默认</el-button>
          <el-button type="primary" round @click="saveLevel">保存设置</el-button>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

const { isAuthenticated, displayName, openAuth } = useAuth()
const { knownWordsOptionGroups, getKnownWordsLabel, getKnownWordsOptionKey, parseKnownWordsOptionKey } = useKnownWordsOptions()
const { defaultKnownWordsSelection, setDefaultKnownWordsSelection } = useUserPreferences()

const selectedOptionKey = ref(getKnownWordsOptionKey(defaultKnownWordsSelection.value))
const selectedSelection = computed(() => parseKnownWordsOptionKey(selectedOptionKey.value))

const selectedKnownWordsLabel = computed(() => (
  getKnownWordsLabel(selectedSelection.value.mode, selectedSelection.value.value)
))
const currentKnownWordsLabel = computed(() => (
  getKnownWordsLabel(defaultKnownWordsSelection.value.mode, defaultKnownWordsSelection.value.value)
))

watch(
  () => defaultKnownWordsSelection.value,
  (value) => {
    selectedOptionKey.value = getKnownWordsOptionKey(value)
  },
  { immediate: true }
)

const resetLevel = () => {
  selectedOptionKey.value = 'coca_rank:3000'
}

const saveLevel = () => {
  setDefaultKnownWordsSelection(selectedSelection.value)
  ElMessage.success(`默认词汇基础已保存为 ${selectedKnownWordsLabel.value}`)
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
}

.settings-layout,
.settings-intro,
.settings-panel,
.intro-stats,
.setting-grid {
  display: grid;
  gap: 20px;
}

.settings-layout {
  max-width: 980px;
}

.settings-intro h1 {
  font-size: clamp(34px, 4vw, 52px);
}

.intro-stats {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.intro-stat,
.setting-card {
  display: grid;
  gap: 8px;
  padding: 20px;
  border-radius: 22px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.intro-stat span,
.field-label {
  color: var(--text-faint);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.intro-stat strong,
.preview-card strong {
  font-size: 24px;
  line-height: 1.04;
}

.compact-heading {
  gap: 14px;
}

.panel-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.preview-card p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.75;
}

.level-select {
  width: 100%;
}

@media (max-width: 860px) {
  .intro-stats,
  .setting-grid {
    grid-template-columns: 1fr;
  }
}
</style>
