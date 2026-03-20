<template>
  <div class="report-page">
    <header class="report-topbar">
      <div class="topbar-links">
        <NuxtLink to="/" class="back-link soft-pill">返回首页</NuxtLink>
        <NuxtLink to="/vocabulary" class="back-link soft-pill">词库</NuxtLink>
        <NuxtLink to="/history" class="back-link soft-pill">书架</NuxtLink>
      </div>
      <div class="report-headline">
        <span class="headline-kicker soft-pill">Result Summary</span>
        <h1>阅读前词汇分析结果</h1>
        <p>查看这本书的词汇负担、95% 覆盖核心词，并直接下载 CSV。</p>
      </div>
    </header>

    <main v-if="jobState === 'loading'" class="loading-state soft-panel">
      <el-skeleton animated :rows="6" />
    </main>

    <main v-else-if="jobState === 'processing'" class="status-layout">
      <section class="processing-hero soft-panel">
        <div class="processing-copy">
          <span class="headline-kicker soft-pill">Analyzing</span>
          <h2>系统正在提取这本书的核心词汇</h2>
          <p>我们会解析 EPUB、统计词频、结合你的 COCA 范围和个人词库，完成后自动跳到结果展示。</p>
          <div class="progress-row">
            <el-progress
              :percentage="progressValue"
              :show-text="false"
              :indeterminate="true"
              :duration="3"
              :stroke-width="10"
            />
            <span>{{ progressMessage }}</span>
          </div>
        </div>

        <div class="processing-meta">
          <div class="meta-card soft-panel">
            <strong>#{{ job?.job_id || '--' }}</strong>
            <span>任务编号</span>
          </div>
          <div class="meta-card soft-panel">
            <strong>{{ getKnownWordsLabel(job?.known_words_level) }}</strong>
            <span>当前已掌握范围</span>
          </div>
          <div class="meta-card soft-panel">
            <strong>{{ pollCount }}</strong>
            <span>已轮询次数</span>
          </div>
        </div>
      </section>
    </main>

    <main v-else-if="jobState === 'failed'" class="error-state soft-panel">
      <h2>分析失败</h2>
      <p>{{ failureMessage }}</p>
      <div class="error-actions">
        <el-button type="primary" round @click="retryJobPolling">重新获取状态</el-button>
        <NuxtLink to="/history">
          <el-button round>回到书架</el-button>
        </NuxtLink>
      </div>
    </main>

    <main v-else-if="result" class="report-layout">
      <section class="summary-grid">
        <MetricCard label="总词数" :value="formatNumber(result.summary.total_word_count)" caption="整本书的词汇总出现次数。" />
        <MetricCard label="唯一词" :value="formatNumber(result.summary.unique_word_count)" caption="去重后的词条数量，用于估算阅读面。" />
        <MetricCard label="待记忆词" :value="formatNumber(result.summary.to_memorize_word_count)" caption="已排除已掌握范围后，建议关注的词数。" />
        <MetricCard label="95% 覆盖" :value="formatNumber(result.summary.coverage_95_word_count)" caption="达到 95% 覆盖所需的核心待记忆词数量。" accent />
      </section>

      <section class="hero-band soft-panel">
        <div class="hero-band-copy">
          <span class="book-chip soft-pill">{{ result.book.original_filename }}</span>
          <h2>{{ result.reading_advice.label }}</h2>
          <p>{{ result.reading_advice.message }}</p>
          <div class="meta-row">
            <div>
              <strong>{{ getKnownWordsLabel(result.known_words_level) }}</strong>
              <span>当前已掌握范围</span>
            </div>
            <div>
              <strong>{{ formatDate(result.created_at) }}</strong>
              <span>分析时间</span>
            </div>
          </div>
        </div>
        <div class="advice-shell" :class="result.reading_advice.level">
          <span class="advice-eyebrow">Reading Advice</span>
          <strong>{{ result.reading_advice.label }}</strong>
          <p>{{ result.reading_advice.message }}</p>
        </div>
      </section>

      <section class="download-grid">
        <article v-for="download in downloadCards" :key="download.key" class="download-card soft-panel">
          <span class="download-label">{{ download.label }}</span>
          <h3>{{ download.title }}</h3>
          <p>{{ download.description }}</p>
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
    </main>

    <main v-else class="error-state soft-panel">
      <h2>没有找到分析结果</h2>
      <p>请先从首页上传书籍并完成分析。</p>
      <NuxtLink to="/">
        <el-button type="primary" round>回到首页</el-button>
      </NuxtLink>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

type AnalysisJob = {
  job_id: number
  book_id: number
  status: string
  known_words_level: number
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
  known_words_level: number
  created_at: string
  downloads: Record<string, string>
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
  }
])

const progressValue = computed(() => Math.min(18 + pollCount.value * 9, 92))

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
  jobState.value = 'completed'
}

const loadJobAndMaybeResult = async (jobId: string) => {
  const response = await request<AnalysisJob>(`/analysis/jobs/${jobId}`)
  job.value = response

  if (response.status === 'completed' && response.result_id) {
    result.value = await request<AnalysisResult>(`/analysis/results/${response.result_id}`)
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

const handleDownload = async (key: string, filename: string) => {
  if (!result.value) {
    return
  }
  downloading.value = key
  try {
    await downloadFile(result.value.downloads[key], filename)
  } catch (error: any) {
    ElMessage.error(error?.message || '下载失败')
  } finally {
    downloading.value = ''
  }
}

watch(
  () => route.fullPath,
  async () => {
    result.value = null
    job.value = null
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
  width: min(1180px, 100%);
  margin: 0 auto;
  padding: 24px 20px 48px;
}

.report-topbar,
.topbar-links,
.hero-band,
.meta-row,
.processing-hero,
.processing-meta,
.error-actions {
  display: flex;
}

.report-topbar {
  align-items: start;
  justify-content: space-between;
  gap: 24px;
}

.topbar-links {
  gap: 12px;
  flex-wrap: wrap;
}

.back-link {
  padding: 12px 18px;
  color: var(--text-main);
}

.headline-kicker,
.book-chip {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 10px 16px;
  color: var(--accent-600);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.report-headline {
  flex: 1;
}

.report-headline h1 {
  margin: 18px 0 10px;
  font-size: clamp(40px, 5vw, 64px);
  line-height: 0.96;
  letter-spacing: -0.05em;
}

.report-headline p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.8;
}

.loading-state,
.error-state {
  margin-top: 26px;
  padding: 28px;
}

.status-layout,
.report-layout {
  display: grid;
  gap: 22px;
  margin-top: 26px;
}

.processing-hero,
.hero-band {
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
}

.processing-copy,
.hero-band-copy {
  display: grid;
  gap: 16px;
  max-width: 680px;
}

.processing-copy h2,
.hero-band-copy h2 {
  margin: 0;
  font-size: clamp(28px, 4vw, 46px);
  line-height: 1;
}

.processing-copy p,
.hero-band-copy p {
  margin: 0;
  color: var(--text-main);
  line-height: 1.9;
}

.progress-row {
  display: grid;
  gap: 10px;
  margin-top: 8px;
}

.progress-row span {
  color: var(--text-soft);
}

.processing-meta {
  flex-direction: column;
  gap: 14px;
  min-width: 260px;
}

.meta-card {
  display: grid;
  gap: 6px;
  padding: 20px;
}

.meta-card strong {
  font-size: 24px;
}

.meta-card span,
.meta-row span,
.error-state p {
  color: var(--text-soft);
}

.summary-grid,
.download-grid {
  display: grid;
  gap: 18px;
}

.summary-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.meta-row {
  gap: 20px;
  flex-wrap: wrap;
}

.meta-row div {
  display: grid;
  gap: 6px;
}

.meta-row strong {
  font-size: 18px;
}

.advice-shell {
  min-width: 280px;
  padding: 24px;
  border-radius: var(--radius-md);
  color: var(--text-inverse);
  background: linear-gradient(160deg, rgba(58, 141, 255, 0.88), rgba(77, 201, 170, 0.72));
  box-shadow: var(--shadow-card);
}

.advice-shell.level_3 {
  background: linear-gradient(160deg, rgba(255, 123, 123, 0.9), rgba(240, 180, 81, 0.78));
}

.advice-shell.level_1 {
  background: linear-gradient(160deg, rgba(77, 201, 170, 0.92), rgba(58, 141, 255, 0.74));
}

.advice-eyebrow {
  display: block;
  margin-bottom: 16px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  opacity: 0.86;
}

.advice-shell strong {
  display: block;
  font-size: 28px;
  line-height: 1.06;
}

.advice-shell p {
  margin: 14px 0 0;
  line-height: 1.8;
  color: rgba(245, 251, 255, 0.82);
}

.download-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.download-card {
  display: grid;
  gap: 14px;
  padding: 24px;
}

.download-label {
  color: var(--primary-600);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.download-card h3 {
  margin: 0;
  font-size: 24px;
}

.download-card p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.8;
}

.error-actions {
  gap: 12px;
  margin-top: 18px;
  flex-wrap: wrap;
}

@media (max-width: 1024px) {
  .summary-grid,
  .download-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .processing-hero,
  .hero-band {
    flex-direction: column;
  }
}

@media (max-width: 720px) {
  .report-page {
    padding-inline: 14px;
  }

  .report-topbar,
  .summary-grid,
  .download-grid {
    grid-template-columns: 1fr;
    display: grid;
  }

  .report-headline h1 {
    font-size: 36px;
  }

  .processing-hero,
  .hero-band,
  .loading-state,
  .error-state {
    padding: 20px;
  }
}
</style>
