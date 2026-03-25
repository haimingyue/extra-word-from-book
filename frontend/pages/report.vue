<template>
  <div class="app-shell section-stack report-page">
    <AppNavigation />

    <PageHero
      eyebrow="Result"
      title="阅读前词汇分析结果"
      description="查看这本书的词汇负担、95% 覆盖核心词和阅读建议，并直接下载三份 CSV。"
      :stats="reportStats"
    />

    <section v-if="jobState === 'loading'" class="surface-panel page-card">
      <el-skeleton animated :rows="6" />
    </section>

    <section v-else-if="jobState === 'processing'" class="status-panel surface-panel page-card">
      <div class="section-heading">
        <span class="eyebrow">Analyzing</span>
        <h2>系统正在提取这本书的核心词汇</h2>
        <p>我们会解析 EPUB、统计词频，并结合你选择的考试标签或 COCA 档位与个人词库，完成后自动跳到结果展示。</p>
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
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
  .band-meta {
    grid-template-columns: 1fr;
  }
}
</style>
