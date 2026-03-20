<template>
  <div class="home-page">
    <header class="topbar">
      <div class="brand-row">
        <div class="brand-mark soft-panel">
          <span>Lexi</span>
        </div>
        <div>
          <strong>单词提取学习</strong>
          <p>把读书前最该记忆的词先挑出来，再进入阅读状态。</p>
        </div>
      </div>

      <div class="topbar-actions">
        <button class="theme-toggle soft-pill" type="button" @click="toggleTheme">
          <span>{{ theme === 'light' ? '浅色' : '暗色' }}</span>
        </button>
        <template v-if="isAuthenticated">
          <NuxtLink to="/vocabulary">
            <el-button round>词库</el-button>
          </NuxtLink>
          <NuxtLink to="/history">
            <el-button round>书架</el-button>
          </NuxtLink>
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

    <main class="hero-layout">
      <section class="hero-copy">
        <div class="hero-kicker soft-pill">
          <span>Soft UI Learning Suite</span>
        </div>
        <h1>
          在阅读前，先提取
          <span>最值得学的词</span>
        </h1>
        <p>
          上传英文 EPUB，结合 COCA 已掌握范围和个人词库，
          自动筛出待记忆单词、95% 覆盖核心词，并给出是否适合立即阅读的判断。
        </p>

        <div class="hero-actions">
          <el-button type="primary" round size="large" :loading="submitting" @click="startAnalysis">
            开始分析这本书
          </el-button>
          <el-button round size="large" @click="triggerBookSelect">先选 EPUB</el-button>
        </div>

        <div class="insight-grid">
          <MetricCard label="95% 覆盖" value="核心词优先" caption="自动提取先学词，减少进入阅读前的准备成本。" />
          <MetricCard label="个人词库" value="TXT 导入" caption="支持导入你的已掌握词表，分析更贴近真实水平。" />
          <MetricCard label="阅读建议" value="三级判断" caption="强推荐、推荐学习、不建议直读，一眼给出答案。" accent />
        </div>
      </section>

      <section class="hero-panel soft-panel">
        <div class="panel-header">
          <div>
            <span class="panel-label">学习入口</span>
            <h2>上传书籍并建立你的阅读前词表</h2>
          </div>
          <div class="status-chip soft-pill">
            <span>{{ isAuthenticated ? '已登录，可直接提交' : '可先准备，提交时登录' }}</span>
          </div>
        </div>

        <div class="panel-grid">
          <article class="upload-tile soft-panel upload-hero">
            <div class="tile-top">
              <div class="icon-shell">EPUB</div>
              <span class="tile-step">Step 1</span>
            </div>
            <h3>选择英文书籍</h3>
            <p>支持 `.epub`，点击后只在本地选择文件，真正提交发生在分析开始时。</p>
            <button class="upload-button" type="button" @click="triggerBookSelect">
              <span>{{ selectedBookName || '选择 EPUB 文件' }}</span>
            </button>
          </article>

          <article class="upload-tile soft-panel">
            <div class="tile-top">
              <div class="icon-shell">TXT</div>
              <span class="tile-step">Step 2</span>
            </div>
            <h3>导入已掌握词库</h3>
            <p>支持一行一个词，或你现在使用的 tab 分隔导出格式。</p>
            <button class="upload-button" type="button" @click="triggerVocabularySelect">
              <span>{{ selectedVocabularyName || '选择 TXT 文件' }}</span>
            </button>
            <el-button
              round
              class="sync-button"
              :loading="uploadingVocabulary"
              @click="syncVocabulary"
            >
              同步到我的词库
            </el-button>
          </article>

          <article class="upload-tile soft-panel">
            <div class="tile-top">
              <div class="icon-shell">COCA</div>
              <span class="tile-step">Step 3</span>
            </div>
            <h3>设置已掌握范围</h3>
            <p>从 COCA 1000 到 15000，帮助系统推断这本书对你的真实难度。</p>
            <el-select v-model="knownWordsLevel" size="large" class="level-select">
              <el-option
                v-for="level in knownWordLevels"
                :key="level"
                :label="`COCA ${level}`"
                :value="level"
              />
            </el-select>
          </article>
        </div>

        <div class="trust-row">
          <div class="trust-item">
            <strong>{{ selectedBookName ? '已选择' : '等待中' }}</strong>
            <span>书籍文件</span>
          </div>
          <div class="trust-item">
            <strong>{{ selectedVocabularyName ? '已准备' : '可选' }}</strong>
            <span>个人词库</span>
          </div>
          <div class="trust-item">
            <strong>COCA {{ knownWordsLevel }}</strong>
            <span>当前范围</span>
          </div>
        </div>
      </section>
    </main>

    <input ref="bookInputRef" type="file" accept=".epub" hidden @change="onBookSelected">
    <input ref="vocabularyInputRef" type="file" accept=".txt" hidden @change="onVocabularySelected">
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

const router = useRouter()
const { theme, toggleTheme } = useTheme()
const {
  isAuthenticated,
  displayName,
  openAuth,
  clearAuth
} = useAuth()
const { request } = useApi()

const bookInputRef = ref<HTMLInputElement | null>(null)
const vocabularyInputRef = ref<HTMLInputElement | null>(null)
const selectedBookFile = ref<File | null>(null)
const selectedVocabularyFile = ref<File | null>(null)
const submitting = ref(false)
const uploadingVocabulary = ref(false)
const knownWordsLevel = ref(3000)

const knownWordLevels = [1000, 2000, 3000, 5000, 8000, 10000, 12000, 15000]

const selectedBookName = computed(() => selectedBookFile.value?.name || '')
const selectedVocabularyName = computed(() => selectedVocabularyFile.value?.name || '')

const triggerBookSelect = () => {
  bookInputRef.value?.click()
}

const triggerVocabularySelect = () => {
  vocabularyInputRef.value?.click()
}

const onBookSelected = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) {
    return
  }
  selectedBookFile.value = file
  ElMessage.success(`已选择书籍：${file.name}`)
}

const onVocabularySelected = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) {
    return
  }
  selectedVocabularyFile.value = file
  ElMessage.success(`已准备词库：${file.name}`)
}

const uploadBook = async () => {
  if (!selectedBookFile.value) {
    throw new Error('请先选择 EPUB 文件')
  }
  const formData = new FormData()
  formData.append('file', selectedBookFile.value)
  return request<{ book_id: number; original_filename: string; title?: string; language?: string; is_duplicate: boolean }>(
    '/books/upload',
    {
      method: 'POST',
      body: formData
    }
  )
}

const syncVocabulary = async () => {
  if (!selectedVocabularyFile.value) {
    ElMessage.warning('请先选择 TXT 词库文件')
    return false
  }

  if (!isAuthenticated.value) {
    openAuth('login', syncVocabulary)
    return false
  }

  uploadingVocabulary.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedVocabularyFile.value)
    const result = await request<{ vocabulary_id: number; name: string; imported_count: number; deduplicated_count: number }>(
      '/vocabularies/upload',
      {
        method: 'POST',
        body: formData
      }
    )
    ElMessage.success(`词库已同步：新增 ${result.imported_count} 个词`)
    return true
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '词库上传失败')
    return false
  } finally {
    uploadingVocabulary.value = false
  }
}

const startAnalysis = async () => {
  if (!selectedBookFile.value) {
    ElMessage.warning('请先选择 EPUB 文件')
    return
  }

  if (!isAuthenticated.value) {
    openAuth('login', startAnalysis)
    return
  }

  submitting.value = true
  try {
    if (selectedVocabularyFile.value) {
      const uploaded = await syncVocabulary()
      if (!uploaded) {
        return
      }
    }

    const uploadedBook = await uploadBook()
    const job = await request<{
      job_id: number
      book_id: number
      status: string
      known_words_level: number
      result_id?: number | null
    }>('/analysis/jobs', {
      method: 'POST',
      body: {
        book_id: uploadedBook.book_id,
        known_words_level: knownWordsLevel.value
      }
    })

    await router.push({
      path: '/report',
      query: {
        jobId: String(job.job_id)
      }
    })
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '分析失败')
  } finally {
    submitting.value = false
  }
}

const handleLogout = () => {
  clearAuth()
  ElMessage.success('已退出登录')
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  padding: 20px 20px 48px;
}

.topbar,
.hero-layout {
  width: min(1200px, 100%);
  margin: 0 auto;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 8px 0 28px;
}

.brand-row,
.topbar-actions,
.hero-actions,
.tile-top,
.trust-row {
  display: flex;
  align-items: center;
}

.brand-row {
  gap: 16px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border-radius: 24px;
  color: var(--primary-600);
  font-weight: 800;
  letter-spacing: 0.08em;
}

.brand-row strong {
  display: block;
  font-size: 18px;
}

.brand-row p {
  margin: 4px 0 0;
  color: var(--text-soft);
}

.topbar-actions {
  gap: 12px;
}

.theme-toggle,
.user-chip {
  padding: 10px 16px;
  border: 0;
  color: var(--text-main);
}

.hero-layout {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 28px;
  align-items: start;
}

.hero-copy {
  padding: 28px 4px 0;
}

.hero-kicker,
.status-chip {
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
.panel-header h2 {
  margin: 18px 0 0;
  font-size: clamp(42px, 6vw, 74px);
  line-height: 0.96;
  letter-spacing: -0.06em;
}

.hero-copy h1 span {
  color: var(--primary-600);
}

.hero-copy > p {
  max-width: 620px;
  margin: 22px 0 0;
  color: var(--text-main);
  font-size: 17px;
  line-height: 1.9;
}

.hero-actions {
  gap: 14px;
  margin-top: 28px;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin-top: 38px;
}

.hero-panel {
  padding: 28px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: start;
}

.panel-label {
  color: var(--accent-600);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.panel-header h2 {
  margin-top: 12px;
  font-size: clamp(28px, 4vw, 42px);
}

.panel-grid {
  display: grid;
  gap: 18px;
  margin-top: 28px;
}

.upload-tile {
  padding: 22px;
}

.upload-hero {
  background:
    radial-gradient(circle at top right, rgba(77, 201, 170, 0.18), transparent 28%),
    var(--surface-1);
}

.tile-top {
  justify-content: space-between;
}

.icon-shell {
  display: inline-grid;
  place-items: center;
  min-width: 58px;
  height: 40px;
  padding: 0 12px;
  border-radius: 16px;
  background: rgba(58, 141, 255, 0.12);
  color: var(--primary-600);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
}

.tile-step {
  color: var(--text-soft);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.upload-tile h3 {
  margin: 18px 0 10px;
  font-size: 24px;
}

.upload-tile p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.8;
}

.upload-button {
  width: 100%;
  margin-top: 20px;
  padding: 18px 20px;
  border: 1px dashed var(--border-strong);
  border-radius: 22px;
  background: var(--surface-3);
  color: var(--text-main);
  text-align: left;
  box-shadow: var(--shadow-inset);
  cursor: pointer;
}

.sync-button,
.level-select {
  margin-top: 18px;
  width: 100%;
}

.trust-row {
  justify-content: space-between;
  gap: 12px;
  margin-top: 20px;
  padding: 18px 4px 4px;
}

.trust-item {
  display: grid;
  gap: 6px;
}

.trust-item strong {
  font-size: 18px;
}

.trust-item span {
  color: var(--text-soft);
  font-size: 13px;
}

@media (max-width: 1120px) {
  .hero-layout {
    grid-template-columns: 1fr;
  }

  .hero-copy {
    padding-top: 8px;
  }

  .insight-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .home-page {
    padding-inline: 14px;
  }

  .topbar,
  .brand-row,
  .topbar-actions,
  .hero-actions,
  .trust-row {
    flex-wrap: wrap;
  }

  .hero-copy h1 {
    font-size: 40px;
  }

  .hero-copy > p {
    font-size: 15px;
  }

  .hero-panel {
    padding: 20px;
  }
}
</style>
