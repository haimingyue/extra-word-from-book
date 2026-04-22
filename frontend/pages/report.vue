<template>
  <div class="app-shell section-stack report-page">
    <AppNavigation />

    <PageHero
      eyebrow="Result"
      title="阅读前词汇分析结果"
      description="查看这本书的词汇负担、95% 覆盖核心词和阅读建议，并直接下载四份 CSV。"
      :stats="reportStats"
    />

    <section v-if="jobState === 'loading'" class="surface-panel page-card">
      <el-skeleton animated :rows="6" />
    </section>

    <section v-else-if="jobState === 'processing'" class="status-panel surface-panel page-card">
      <div class="section-heading">
        <span class="eyebrow">Analyzing</span>
        <h2>系统正在提取这本书的核心词汇</h2>
        <p>我们会解析 EPUB 或纯英文 TXT、统计词频，并结合你选择的考试标签或 COCA 档位与个人词库，完成后自动跳到结果展示。</p>
      </div>

      <div class="processing-grid">
        <div class="progress-panel">
          <el-progress
            :percentage="progressValue"
            :show-text="false"
            :indeterminate="true"
            :duration="3"
            :stroke-width="10"
          />
          <strong>{{ progressMessage }}</strong>
          <p class="muted-copy">任务执行中请不要关闭页面，系统会自动轮询并在完成后展示结果。</p>
        </div>

        <div class="meta-list">
          <article class="meta-card">
            <span>任务编号</span>
            <strong>#{{ job?.job_id || '--' }}</strong>
          </article>
          <article class="meta-card">
            <span>已掌握范围</span>
            <strong>{{ getKnownWordsLabel(job?.known_words_mode, job?.known_words_value) }}</strong>
          </article>
          <article class="meta-card">
            <span>已轮询次数</span>
            <strong>{{ pollCount }}</strong>
          </article>
        </div>
      </div>
    </section>

    <EmptyStateCard
      v-else-if="jobState === 'failed'"
      eyebrow="Failed"
      title="分析失败"
      :description="failureMessage"
    >
      <template #actions>
        <el-button type="primary" round @click="retryJobPolling">重新获取状态</el-button>
        <NuxtLink to="/history">
          <el-button round>回到书架</el-button>
        </NuxtLink>
      </template>
    </EmptyStateCard>

    <template v-else-if="result">
      <section class="app-grid-4">
        <MetricCard label="总词数" :value="formatNumber(result.summary.total_word_count)" caption="整本书的词汇总出现次数。" />
        <MetricCard label="唯一词" :value="formatNumber(result.summary.unique_word_count)" caption="去重后的词条数量，用于估算阅读面。" />
        <MetricCard label="待记忆词" :value="formatNumber(result.summary.to_memorize_word_count)" caption="已排除已掌握范围后，建议重点关注的词数。" />
        <MetricCard label="95% 覆盖" :value="formatNumber(result.summary.coverage_95_word_count)" caption="达到 95% 覆盖所需的核心待记忆词数量。" accent />
      </section>

      <section class="report-band">
        <article class="surface-panel page-card band-main">
          <div class="section-heading">
            <span class="surface-tag">{{ result.book.original_filename }}</span>
            <h2>{{ result.reading_advice.label }}</h2>
            <p>{{ result.reading_advice.message }}</p>
          </div>

          <div class="band-meta">
            <article class="meta-card">
              <span>当前已掌握范围</span>
              <strong>{{ getKnownWordsLabel(result.known_words_mode, result.known_words_value) }}</strong>
            </article>
            <article class="meta-card">
              <span>分析时间</span>
              <strong>{{ formatDate(result.created_at) }}</strong>
            </article>
          </div>
        </article>

        <article class="surface-panel page-card advice-panel" :class="result.reading_advice.level">
          <span class="eyebrow advice-eyebrow">Reading Advice</span>
          <strong>{{ result.reading_advice.label }}</strong>
          <p>{{ result.reading_advice.message }}</p>
        </article>
      </section>

      <WordDistributionChart :result-id="result.result_id" />

      <section class="download-grid">
        <article v-for="download in downloadCards" :key="download.key" class="surface-panel page-card download-card">
          <span class="eyebrow">{{ download.label }}</span>
          <div class="section-heading compact-copy">
            <h3>{{ download.title }}</h3>
            <p>{{ download.description }}</p>
          </div>
          <el-button
            round
            type="primary"
            :loading="downloading === download.key"
            @click="handleDownload(download.key, download.filename)"
          >
            下载 {{ download.filename }}
          </el-button>
        </article>
      </section>

      <section v-if="result.chapter_analysis_supported" class="chapter-section">
        <div class="section-heading">
          <span class="eyebrow">Chapters</span>
          <h2>按章节查看词汇负担</h2>
          <p>章节分析目前仅支持 EPUB。点击任意章节，打开详情弹框查看指标、分布曲线和本章导出。</p>
        </div>

        <article class="surface-panel page-card chapter-list-panel">
          <div class="chapter-list-header">
            <strong>章节概览</strong>
            <span>{{ chapters.length }} 章</span>
          </div>

          <div v-if="chaptersLoading" class="chapter-empty">
            <el-skeleton animated :rows="5" />
          </div>

          <div v-else-if="!chapters.length" class="chapter-empty">
            <p>当前 EPUB 没有提取到可展示的有效章节。</p>
          </div>

          <template v-else>
            <button
              v-for="chapter in chapters"
              :key="chapter.chapter_id"
              type="button"
              class="chapter-item"
              @click="openChapter(chapter.chapter_id)"
            >
              <div class="chapter-item-top">
                <strong>{{ chapter.chapter_index }}. {{ chapter.chapter_title }}</strong>
                <span>{{ formatNumber(chapter.coverage_95_word_count) }} 核心词</span>
              </div>
              <div class="chapter-item-meta">
                <span>总词数 {{ formatNumber(chapter.total_word_count) }}</span>
                <span>待记忆 {{ formatNumber(chapter.to_memorize_word_count) }}</span>
                <span>{{ chapter.reading_advice.label }}</span>
              </div>
            </button>
          </template>
        </article>
      </section>
    </template>

    <EmptyStateCard
      v-else
      eyebrow="Empty"
      title="没有找到分析结果"
      description="请先从首页上传书籍并完成分析。"
    >
      <template #actions>
        <NuxtLink to="/">
          <el-button type="primary" round>回到首页</el-button>
        </NuxtLink>
      </template>
    </EmptyStateCard>

    <el-dialog
      v-model="chapterDialogVisible"
      width="min(1120px, calc(100vw - 32px))"
      class="chapter-dialog"
      :show-close="true"
      destroy-on-close
    >
      <template #header>
        <div class="chapter-dialog-header">
          <div>
            <span v-if="activeChapter" class="surface-tag">Chapter {{ activeChapter.chapter.chapter_index }}</span>
            <h2>{{ activeChapter?.chapter.chapter_title || '章节详情' }}</h2>
            <p>{{ activeChapter?.chapter.reading_advice.message || '正在加载章节详情...' }}</p>
          </div>
          <div v-if="activeChapter" class="chapter-dialog-badge" :class="activeChapter.chapter.reading_advice.level">
            <span>阅读建议</span>
            <strong>{{ activeChapter.chapter.reading_advice.label }}</strong>
          </div>
        </div>
      </template>

      <div v-if="chapterDetailLoading" class="chapter-empty chapter-dialog-loading">
        <el-skeleton animated :rows="10" />
      </div>

      <template v-else-if="activeChapter">
        <section class="chapter-hero">
          <div class="chapter-hero-copy">
            <span class="eyebrow">Chapter Insight</span>
            <h3>{{ activeChapter.chapter.chapter_title }}</h3>
            <p>查看这一章的阅读负担、COCA 档位分布，以及专属词表下载入口。</p>
          </div>
          <div class="chapter-hero-orbit">
            <div class="chapter-hero-ring">
              <span>95%</span>
              <strong>{{ formatNumber(activeChapter.chapter.coverage_95_word_count) }}</strong>
              <small>核心待记忆词</small>
            </div>
          </div>
        </section>

        <section class="chapter-metrics">
          <article class="meta-card chapter-metric-card">
            <span>总词数</span>
            <strong>{{ formatNumber(activeChapter.chapter.total_word_count) }}</strong>
          </article>
          <article class="meta-card chapter-metric-card">
            <span>唯一词</span>
            <strong>{{ formatNumber(activeChapter.chapter.unique_word_count) }}</strong>
          </article>
          <article class="meta-card chapter-metric-card">
            <span>待记忆词</span>
            <strong>{{ formatNumber(activeChapter.chapter.to_memorize_word_count) }}</strong>
          </article>
          <article class="meta-card chapter-metric-card">
            <span>核心词</span>
            <strong>{{ formatNumber(activeChapter.chapter.coverage_95_word_count) }}</strong>
          </article>
        </section>

        <WordDistributionChart
          :distribution-path="`/analysis/results/${activeChapter.result_id}/chapters/${activeChapter.chapter.chapter_id}/distribution`"
          title="本章词汇分布曲线"
          description="横轴为 COCA 分档，纵轴为该档位单词在本章中的累计出现次数。"
          note="灰色/未知档表示没有匹配到 COCA 排名的词，可据此判断本章生词集中在哪些频段。"
        />

        <section class="chapter-download-panel">
          <div class="section-heading compact-copy">
            <span class="eyebrow">Chapter CSV</span>
            <h3>下载这一章的学习材料</h3>
            <p>保留与整本书一致的 4 种导出格式，适合按章节推进阅读和记忆。</p>
          </div>

          <div class="chapter-downloads">
            <div
              v-for="download in downloadCards"
              :key="`chapter-${download.key}`"
              class="chapter-download-row"
            >
              <el-button
                round
                size="large"
                class="chapter-download-button"
                :loading="downloading === `chapter:${download.key}`"
                @click="handleChapterDownload(download.key, download.filename)"
              >
                下载本章 {{ download.filename }}
              </el-button>
              <el-button
                v-if="download.key === 'coverage_95_anki'"
                round
                size="large"
                type="primary"
                plain
                :loading="importingChapterWords"
                @click="handleImportChapterWords"
              >
                添加到个人词库
              </el-button>
            </div>
          </div>

          <div v-if="showReanalyzeAfterImport" class="chapter-reanalyze-bar">
            <div class="compact-copy">
              <strong>个人词库已更新</strong>
              <p>现在可以基于当前已掌握范围和最新词库，重新分析这本书。</p>
            </div>
            <el-button
              type="primary"
              round
              size="large"
              :loading="restartingAnalysis"
              @click="handleReanalyzeCurrentBook"
            >
              重新分析本书
            </el-button>
          </div>
        </section>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

type AnalysisJob = {
  job_id: number
  book_id: number
  status: string
  known_words_mode: 'exam_level' | 'coca_rank'
  known_words_value: string
  error_code?: string | null
  error_message?: string | null
  queued_at: string
  started_at?: string | null
  finished_at?: string | null
  result_id?: number | null
}

type AnalysisResult = {
  result_id: number
  job_id: number
  book: {
    book_id: number
    file_type: 'epub' | 'txt'
    title?: string | null
    original_filename: string
  }
  summary: {
    total_word_count: number
    unique_word_count: number
    to_memorize_word_count: number
    coverage_95_word_count: number
  }
  reading_advice: {
    level: string
    label: string
    color: string
    message: string
  }
  known_words_mode: 'exam_level' | 'coca_rank'
  known_words_value: string
  created_at: string
  downloads: Record<string, string>
  chapter_analysis_supported: boolean
}

type ChapterSummary = {
  chapter_id: number
  chapter_index: number
  chapter_title: string
  total_word_count: number
  unique_word_count: number
  to_memorize_word_count: number
  coverage_95_word_count: number
  reading_advice: {
    level: string
    label: string
    color: string
    message: string
  }
}

type ChapterListResponse = {
  supported: boolean
  items: ChapterSummary[]
}

type ChapterDetail = {
  result_id: number
  chapter: ChapterSummary
  downloads: Record<string, string>
}

type ChapterVocabularyImportResponse = {
  vocabulary_id: number
  name: string
  imported_count: number
  deduplicated_count: number
}

type JobState = 'loading' | 'processing' | 'completed' | 'failed' | 'empty'

const route = useRoute()
const router = useRouter()
const { request, downloadFile } = useApi()
const { getKnownWordsLabel } = useKnownWordsOptions()

const jobState = ref<JobState>('loading')
const downloading = ref('')
const result = ref<AnalysisResult | null>(null)
const job = ref<AnalysisJob | null>(null)
const chapters = ref<ChapterSummary[]>([])
const chaptersLoading = ref(false)
const activeChapter = ref<ChapterDetail | null>(null)
const chapterDetailLoading = ref(false)
const chapterDialogVisible = ref(false)
const importingChapterWords = ref(false)
const showReanalyzeAfterImport = ref(false)
const restartingAnalysis = ref(false)
const failureMessage = ref('分析失败，请稍后重试。')
const pollCount = ref(0)
const pollTimer = ref<ReturnType<typeof setTimeout> | null>(null)

const downloadCards = computed(() => [
  {
    key: 'all_words',
    label: 'Complete List',
    title: '完整单词列表',
    description: '适合全量浏览这本书的词汇结构与词频分布。',
    filename: 'all_words.csv'
  },
  {
    key: 'to_memorize',
    label: 'Study List',
    title: '待记忆单词列表',
    description: '已经扣除了当前已掌握范围，更适合进入学习软件。',
    filename: 'to_memorize.csv'
  },
  {
    key: 'coverage_95',
    label: 'Core Coverage',
    title: '95% 覆盖核心词',
    description: '优先记忆这部分词，最快进入可阅读状态。',
    filename: 'coverage_95.csv'
  },
  {
    key: 'coverage_95_anki',
    label: 'Anki Import',
    title: '95% 单词导入 Anki 版',
    description: '仅保留单词、排行与 tag 三列，并自动去除 COCA 排行为空的单词。',
    filename: 'coverage_95_anki.csv'
  }
])

const progressValue = computed(() => Math.min(18 + pollCount.value * 9, 92))
const reportStats = computed(() => [
  { label: '任务状态', value: jobState.value === 'completed' ? '已完成' : jobState.value === 'processing' ? '分析中' : '等待中' },
  { label: '结果编号', value: result.value?.result_id || '--' },
  { label: '轮询次数', value: pollCount.value }
])

const progressMessage = computed(() => {
  if (!job.value) {
    return '正在准备分析任务...'
  }
  if (job.value.status === 'pending') {
    return '任务已创建，正在进入分析队列。'
  }
  if (job.value.status === 'processing') {
    return '正在提取文本、计算词频并生成 CSV。'
  }
  return '正在获取最新状态。'
})

const formatNumber = (value: number) => new Intl.NumberFormat('zh-CN').format(value)
const formatDate = (value: string) => new Date(value).toLocaleString('zh-CN')

const clearPollTimer = () => {
  if (pollTimer.value) {
    clearTimeout(pollTimer.value)
    pollTimer.value = null
  }
}

const scheduleNextPoll = () => {
  clearPollTimer()
  pollTimer.value = setTimeout(() => {
    void loadResult()
  }, 2000)
}

const loadResultById = async (resultId: string) => {
  result.value = await request<AnalysisResult>(`/analysis/results/${resultId}`)
  await loadChapters()
  jobState.value = 'completed'
}

const loadJobAndMaybeResult = async (jobId: string) => {
  const response = await request<AnalysisJob>(`/analysis/jobs/${jobId}`)
  job.value = response

  if (response.status === 'completed' && response.result_id) {
    result.value = await request<AnalysisResult>(`/analysis/results/${response.result_id}`)
    await loadChapters()
    jobState.value = 'completed'
    if (route.query.resultId !== String(response.result_id)) {
      await router.replace({
        path: '/report',
        query: {
          jobId: String(response.job_id),
          resultId: String(response.result_id)
        }
      })
    }
    return
  }

  if (response.status === 'failed' || response.status === 'canceled') {
    jobState.value = 'failed'
    failureMessage.value = response.error_message || '分析任务执行失败，请稍后重试。'
    return
  }

  jobState.value = 'processing'
  pollCount.value += 1
  scheduleNextPoll()
}

const loadResult = async () => {
  clearPollTimer()
  try {
    const resultId = typeof route.query.resultId === 'string' ? route.query.resultId : ''
    const jobId = typeof route.query.jobId === 'string' ? route.query.jobId : ''

    if (!resultId && !jobId) {
      jobState.value = 'empty'
      return
    }

    if (!result.value) {
      jobState.value = 'loading'
    }

    if (jobId) {
      await loadJobAndMaybeResult(jobId)
      return
    }

    if (resultId) {
      await loadResultById(resultId)
      return
    }
  } catch (error: any) {
    jobState.value = 'failed'
    failureMessage.value = error?.data?.message || error?.message || '结果加载失败'
    ElMessage.error(failureMessage.value)
  }
}

const retryJobPolling = async () => {
  pollCount.value = 0
  await loadResult()
}

const loadChapters = async () => {
  chapters.value = []
  activeChapter.value = null

  if (!result.value?.chapter_analysis_supported) {
    return
  }

  chaptersLoading.value = true
  try {
    const response = await request<ChapterListResponse>(`/analysis/results/${result.value.result_id}/chapters`)
    chapters.value = response.items
  } catch (error: any) {
    ElMessage.error(error?.message || '章节列表加载失败')
  } finally {
    chaptersLoading.value = false
  }
}

const openChapter = async (chapterId: number) => {
  if (!result.value) {
    return
  }
  chapterDialogVisible.value = true
  activeChapter.value = null
  showReanalyzeAfterImport.value = false
  chapterDetailLoading.value = true
  try {
    activeChapter.value = await request<ChapterDetail>(`/analysis/results/${result.value.result_id}/chapters/${chapterId}`)
  } catch (error: any) {
    ElMessage.error(error?.message || '章节详情加载失败')
    chapterDialogVisible.value = false
  } finally {
    chapterDetailLoading.value = false
  }
}

const resolveDownloadPath = (key: string) => {
  if (!result.value) {
    return ''
  }

  const existingPath = result.value.downloads?.[key]
  if (existingPath) {
    return existingPath
  }

  return `/api/v1/analysis/results/${result.value.result_id}/downloads/${key}`
}

const handleDownload = async (key: string, filename: string) => {
  if (!result.value) {
    return
  }
  downloading.value = key
  try {
    await downloadFile(resolveDownloadPath(key), filename)
  } catch (error: any) {
    ElMessage.error(error?.message || '下载失败')
  } finally {
    downloading.value = ''
  }
}

const handleChapterDownload = async (key: string, filename: string) => {
  if (!activeChapter.value) {
    return
  }
  downloading.value = `chapter:${key}`
  try {
    const path = activeChapter.value.downloads?.[key]
    await downloadFile(path, `chapter_${activeChapter.value.chapter.chapter_index}_${filename}`)
  } catch (error: any) {
    ElMessage.error(error?.message || '下载失败')
  } finally {
    downloading.value = ''
  }
}

const handleImportChapterWords = async () => {
  if (!activeChapter.value) {
    return
  }
  importingChapterWords.value = true
  try {
    const response = await request<ChapterVocabularyImportResponse>(
      `/analysis/results/${activeChapter.value.result_id}/chapters/${activeChapter.value.chapter.chapter_id}/import-to-vocabulary`,
      {
        method: 'POST'
      }
    )
    showReanalyzeAfterImport.value = true
    if (response.imported_count > 0) {
      ElMessage.success(`已添加 ${response.imported_count} 个单词到${response.name}`)
      return
    }
    ElMessage.success(`本章核心词已在${response.name}中，无需重复添加`)
  } catch (error: any) {
    ElMessage.error(error?.message || '添加到个人词库失败')
  } finally {
    importingChapterWords.value = false
  }
}

const handleReanalyzeCurrentBook = async () => {
  if (!result.value) {
    return
  }
  restartingAnalysis.value = true
  try {
    const job = await request<{
      job_id: number
      book_id: number
      status: string
      known_words_mode: 'exam_level' | 'coca_rank'
      known_words_value: string
      result_id?: number | null
    }>('/analysis/jobs', {
      method: 'POST',
      body: {
        book_id: result.value.book.book_id,
        known_words_mode: result.value.known_words_mode,
        known_words_value: result.value.known_words_value
      }
    })

    chapterDialogVisible.value = false
    showReanalyzeAfterImport.value = false
    ElMessage.success('已基于最新个人词库重新发起分析')
    await router.replace({
      path: route.path,
      query: { jobId: String(job.job_id) }
    })
  } catch (error: any) {
    ElMessage.error(error?.message || '重新分析失败')
  } finally {
    restartingAnalysis.value = false
  }
}

watch(
  () => route.fullPath,
  async () => {
    result.value = null
    job.value = null
    chapters.value = []
    activeChapter.value = null
    pollCount.value = 0
    await loadResult()
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  clearPollTimer()
})
</script>

<style scoped>
.report-page {
  min-height: 100vh;
}

.status-panel,
.progress-panel,
.meta-list,
.compact-copy {
  display: grid;
  gap: 18px;
}

.processing-grid,
.report-band {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(280px, 0.85fr);
  gap: 20px;
}

.progress-panel,
.meta-card,
.advice-panel {
  padding: 20px;
  border-radius: 22px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.progress-panel strong,
.meta-card strong,
.advice-panel strong {
  font-size: 24px;
  line-height: 1.04;
}

.meta-list {
  align-content: start;
}

.meta-card span {
  color: var(--text-faint);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.band-main,
.download-card {
  display: grid;
  gap: 20px;
}

.band-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.advice-panel {
  align-content: start;
  background: var(--surface-accent);
  color: var(--text-inverse);
  border: none;
}

.advice-panel.level_3 {
  background: linear-gradient(135deg, #ef5a2d 0%, #f5a623 100%);
}

.advice-panel.level_1 {
  background: linear-gradient(135deg, #1fb980 0%, #4e7bff 100%);
}

.advice-eyebrow {
  color: rgba(255, 249, 245, 0.9);
  background: rgba(255, 255, 255, 0.12);
}

.advice-panel p {
  margin: 0;
  color: rgba(255, 249, 245, 0.82);
  line-height: 1.8;
}

.download-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

.chapter-section,
.chapter-list-panel,
.chapter-downloads,
.chapter-download-panel {
  display: grid;
  gap: 18px;
}

.chapter-list-header,
.chapter-item-top,
.chapter-item-meta,
.chapter-metrics,
.chapter-dialog-header,
.chapter-hero {
  display: grid;
  gap: 12px;
}

.chapter-list-header,
.chapter-item-top {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
}

.chapter-item {
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
  border-radius: 20px;
  padding: 18px;
  text-align: left;
  color: inherit;
  transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
}

.chapter-item:hover {
  border-color: rgba(78, 123, 255, 0.38);
  box-shadow: 0 16px 40px rgba(78, 123, 255, 0.1);
  transform: translateY(-2px);
}

.chapter-item-meta,
.chapter-metrics {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.chapter-metrics {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chapter-empty {
  min-height: 140px;
  display: grid;
  align-content: center;
  color: var(--text-faint);
}

.chapter-dialog-header {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  padding-right: 24px;
}

.chapter-dialog-header h2 {
  margin: 12px 0 8px;
  font-size: 34px;
  line-height: 1;
}

.chapter-dialog-header p {
  margin: 0;
  color: var(--text-faint);
}

.chapter-dialog-badge {
  min-width: 180px;
  padding: 18px 20px;
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(31, 185, 128, 0.16) 0%, rgba(78, 123, 255, 0.14) 100%);
  border: 1px solid rgba(78, 123, 255, 0.18);
  display: grid;
  gap: 8px;
}

.chapter-dialog-badge.level_3 {
  background: linear-gradient(135deg, rgba(239, 90, 45, 0.16) 0%, rgba(245, 166, 35, 0.14) 100%);
  border-color: rgba(239, 90, 45, 0.22);
}

.chapter-dialog-badge span {
  color: var(--text-faint);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.chapter-dialog-badge strong {
  font-size: 24px;
  line-height: 1.05;
}

.chapter-hero {
  grid-template-columns: minmax(0, 1.1fr) 280px;
  align-items: center;
  padding: 28px;
  border-radius: 28px;
  background:
    radial-gradient(circle at top left, rgba(78, 123, 255, 0.18), transparent 38%),
    linear-gradient(135deg, rgba(255, 249, 245, 0.98) 0%, rgba(241, 245, 255, 0.96) 100%);
  border: 1px solid rgba(78, 123, 255, 0.14);
}

.chapter-hero-copy h3 {
  margin: 8px 0 10px;
  font-size: 42px;
  line-height: 0.96;
}

.chapter-hero-copy p {
  margin: 0;
  max-width: 540px;
  color: var(--text-faint);
}

.chapter-hero-orbit {
  display: grid;
  place-items: center;
}

.chapter-hero-ring {
  width: 208px;
  height: 208px;
  border-radius: 50%;
  border: 14px solid rgba(78, 123, 255, 0.12);
  box-shadow:
    inset 0 0 0 10px rgba(255, 255, 255, 0.84),
    0 24px 60px rgba(78, 123, 255, 0.12);
  background: radial-gradient(circle at center, rgba(255, 255, 255, 0.94) 0%, rgba(241, 245, 255, 0.92) 100%);
  display: grid;
  place-items: center;
  text-align: center;
}

.chapter-hero-ring span,
.chapter-hero-ring small {
  display: block;
  color: var(--text-faint);
}

.chapter-hero-ring strong {
  font-size: 44px;
  line-height: 0.94;
}

.chapter-metric-card {
  background: linear-gradient(180deg, rgba(241, 245, 255, 0.78) 0%, rgba(255, 255, 255, 0.92) 100%);
}

.chapter-download-panel {
  padding: 24px;
  border-radius: 26px;
  background: linear-gradient(180deg, rgba(241, 245, 255, 0.7) 0%, rgba(255, 255, 255, 0.92) 100%);
  border: 1px solid rgba(78, 123, 255, 0.12);
}

.chapter-download-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.chapter-download-button {
  width: 100%;
}

.chapter-reanalyze-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(78, 123, 255, 0.14);
}

.chapter-dialog-loading {
  min-height: 480px;
}

:deep(.chapter-dialog .el-dialog) {
  border-radius: 32px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 255, 0.98) 100%);
  overflow: hidden;
}

:deep(.chapter-dialog .el-dialog__header) {
  padding: 28px 28px 0;
}

:deep(.chapter-dialog .el-dialog__body) {
  padding: 20px 28px 28px;
  display: grid;
  gap: 22px;
}

.download-card h3 {
  margin: 0;
  font-size: 28px;
  line-height: 1.02;
}

@media (max-width: 1100px) {
  .processing-grid,
  .report-band,
  .download-grid,
  .band-meta,
  .chapter-item-meta,
  .chapter-metrics,
  .chapter-dialog-header,
  .chapter-hero {
    grid-template-columns: 1fr;
  }

  .chapter-download-row {
    grid-template-columns: 1fr;
  }

  .chapter-reanalyze-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .chapter-hero-ring {
    width: 168px;
    height: 168px;
  }

  .chapter-hero-copy h3 {
    font-size: 34px;
  }
}
</style>
