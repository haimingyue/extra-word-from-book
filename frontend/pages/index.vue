<template>
  <div class="app-shell section-stack home-page">
    <AppNavigation />

    <PageHero
      accent
      eyebrow="Reading Workflow"
      title="把阅读前最该解决的词，先抽出来。"
      description="上传英文 EPUB，叠加 COCA 已掌握范围和个人词库，系统会自动生成完整词表、待记忆词表和 95% 覆盖核心词表。"
      :stats="heroStats"
    >
      <template #actions>
        <el-button type="primary" round size="large" :loading="submitting" @click="startAnalysis">
          开始分析这本书
        </el-button>
        <el-button round size="large" @click="triggerBookSelect">先选 EPUB</el-button>
      </template>
    </PageHero>

    <section class="home-grid">
      <div class="section-stack">
        <section class="workflow-panel surface-panel page-card">
          <div class="section-heading">
            <span class="eyebrow">3 Steps</span>
            <h2>一条连续的阅读准备流程</h2>
            <p>每个动作都尽量压缩到最短路径，避免上传、设置和反馈分散在页面不同区域。</p>
          </div>

          <div class="workflow-list">
            <article class="workflow-step workflow-step-highlight">
              <div class="step-head">
                <span class="step-index">01</span>
                <span class="step-type">Book</span>
              </div>
              <h3>选择英文 EPUB</h3>
              <p>先把书准备好，真正上传会在你点击开始分析时完成。</p>
              <button class="file-button" type="button" @click="triggerBookSelect">
                <span>{{ selectedBookName || '选择 EPUB 文件' }}</span>
                <strong>{{ selectedBookName ? '已准备' : '点击选择' }}</strong>
              </button>
            </article>

            <article class="workflow-step">
              <div class="step-head">
                <span class="step-index">02</span>
                <span class="step-type">Vocabulary</span>
              </div>
              <h3>导入个人词库</h3>
              <p>支持一行一个词，或现有 tab 分隔格式。你也可以跳过这步，只用 COCA 范围。</p>
              <button class="file-button" type="button" @click="triggerVocabularySelect">
                <span>{{ selectedVocabularyName || '选择 TXT 文件' }}</span>
                <strong>{{ selectedVocabularyName ? '已准备' : '可选步骤' }}</strong>
              </button>
              <el-button
                round
                class="secondary-action"
                :loading="uploadingVocabulary"
                @click="syncVocabulary"
              >
                同步到我的词库
              </el-button>
            </article>

            <article class="workflow-step">
              <div class="step-head">
                <span class="step-index">03</span>
                <span class="step-type">Level</span>
              </div>
              <h3>设置已掌握范围</h3>
              <p>可以直接选择 COCA 数值档位，也保留常见英语阶段标签供快速切换。</p>
              <el-select v-model="knownWordsLevel" size="large" class="level-select">
                <el-option
                  v-for="option in knownWordsOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </article>
          </div>
        </section>

        <section class="status-panel surface-panel page-card">
          <div class="section-heading">
            <span class="eyebrow">Ready State</span>
            <h2>当前提交状态</h2>
            <p>在真正开始分析前，你可以很快确认这次任务是否已经准备完整。</p>
          </div>

          <div class="status-grid">
            <article class="status-card">
              <span>书籍文件</span>
              <strong>{{ selectedBookName ? '已选择' : '等待中' }}</strong>
              <p>{{ selectedBookName || '还没有选择 EPUB 文件' }}</p>
            </article>
            <article class="status-card">
              <span>个人词库</span>
              <strong>{{ selectedVocabularyName ? '已准备' : '可跳过' }}</strong>
              <p>{{ selectedVocabularyName || '没有选择也可以直接分析' }}</p>
            </article>
            <article class="status-card">
              <span>当前范围</span>
              <strong>{{ currentKnownWordsLabel }}</strong>
              <p>系统会将这一档位与你的个人词库做并集过滤。</p>
            </article>
          </div>
        </section>
      </div>

      <aside class="section-stack">
        <section class="surface-panel page-card aside-panel">
          <div class="section-heading">
            <span class="eyebrow">Why It Works</span>
            <h2>更像产品，而不是工具脚本</h2>
            <p>这套流程的重点不是“导出所有词”，而是尽快告诉你下一步应该学什么、这本书能不能现在读。</p>
          </div>

          <div class="insight-list">
            <div class="insight-item">
              <strong>95% 覆盖优先级</strong>
              <p>先抓最影响阅读流畅度的待记忆词，避免一开始就被完整词表压垮。</p>
            </div>
            <div class="insight-item">
              <strong>个人词库并集过滤</strong>
              <p>你已经掌握但不在 COCA 范围内的词，也会被自动排除掉。</p>
            </div>
            <div class="insight-item">
              <strong>阅读建议直接判断</strong>
              <p>结果页会告诉你这本书是适合直读，还是应该先补少量关键词。</p>
            </div>
          </div>
        </section>

        <div class="app-grid-1 metrics-stack">
          <MetricCard label="95% 覆盖" value="核心词优先" caption="先记最关键的一小部分词，而不是一次性背完整词表。" />
          <MetricCard label="词库同步" value="TXT 导入" caption="支持上传你自己的已掌握词表，让分析更贴近真实水平。" />
          <MetricCard label="阅读判断" value="三级建议" caption="完成分析后立即给出可读性判断，帮助你决定下一本书。 " accent />
        </div>
      </aside>
    </section>

    <input ref="bookInputRef" type="file" accept=".epub" hidden @change="onBookSelected">
    <input ref="vocabularyInputRef" type="file" accept=".txt" hidden @change="onVocabularySelected">
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

const router = useRouter()
const {
  isAuthenticated,
  openAuth
} = useAuth()
const { request } = useApi()
const { knownWordsOptions, getKnownWordsLabel } = useKnownWordsOptions()
const { defaultKnownWordsLevel } = useUserPreferences()

const bookInputRef = ref<HTMLInputElement | null>(null)
const vocabularyInputRef = ref<HTMLInputElement | null>(null)
const selectedBookFile = ref<File | null>(null)
const selectedVocabularyFile = ref<File | null>(null)
const submitting = ref(false)
const uploadingVocabulary = ref(false)
const knownWordsLevel = ref(defaultKnownWordsLevel.value)

const selectedBookName = computed(() => selectedBookFile.value?.name || '')
const selectedVocabularyName = computed(() => selectedVocabularyFile.value?.name || '')
const currentKnownWordsLabel = computed(() => getKnownWordsLabel(knownWordsLevel.value))
const heroStats = computed(() => [
  { label: '已掌握范围', value: currentKnownWordsLabel.value },
  { label: '书籍文件', value: selectedBookName.value ? '已准备' : '待选择' },
  { label: '个人词库', value: selectedVocabularyName.value ? '已准备' : '可选' }
])

watch(
  () => defaultKnownWordsLevel.value,
  (value) => {
    knownWordsLevel.value = value
  },
  { immediate: true }
)

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
</script>

<style scoped>
.home-page {
  min-height: 100vh;
}

.home-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.75fr);
  gap: 24px;
}

.workflow-panel,
.status-panel,
.aside-panel {
  display: grid;
  gap: 24px;
}

.workflow-list,
.status-grid,
.insight-list,
.metrics-stack {
  display: grid;
  gap: 16px;
}

.workflow-step {
  display: grid;
  gap: 14px;
  padding: 22px;
  border-radius: 24px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.workflow-step-highlight {
  background: var(--surface-accent-soft);
}

.step-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.step-index,
.step-type {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.step-index {
  color: var(--accent-600);
}

.step-type {
  color: var(--text-faint);
}

.workflow-step h3,
.status-card strong,
.insight-item strong {
  margin: 0;
}

.workflow-step h3 {
  font-size: 26px;
  line-height: 1.04;
}

.workflow-step p,
.status-card p,
.insight-item p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.75;
}

.file-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  padding: 16px 18px;
  border-radius: 20px;
  border: 1px dashed var(--border-strong);
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-main);
  text-align: left;
}

[data-theme="dark"] .file-button {
  background: rgba(20, 26, 42, 0.78);
}

.file-button strong {
  color: var(--primary-600);
  font-size: 14px;
}

.secondary-action {
  justify-self: start;
}

.level-select {
  width: 100%;
}

.status-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.status-card {
  display: grid;
  gap: 10px;
  padding: 20px;
  border-radius: 22px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.status-card span {
  color: var(--text-faint);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.status-card strong {
  font-size: 24px;
  line-height: 1;
}

.aside-panel {
  min-height: 100%;
}

.insight-item {
  display: grid;
  gap: 8px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-soft);
}

.insight-item:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

.app-grid-1 {
  display: grid;
  gap: 16px;
}

@media (max-width: 1100px) {
  .home-grid,
  .status-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .workflow-step h3 {
    font-size: 22px;
  }

  .file-button {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
