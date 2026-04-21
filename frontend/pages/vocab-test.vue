<template>
  <div class="app-shell section-stack vocab-test-page">
    <AppNavigation />

    <PageHero
      accent
      eyebrow="Vocabulary Test"
      title="用一轮更重的分阶段测评，估出你的 COCA 词汇位置。"
      description="现在每题会同时展示单词和简短释义，并显著增加题量。系统先做全局粗定位，再围绕边界档位大范围加测，最后输出推荐 COCA 档位、预估词汇量和置信度。"
      :stats="heroStats"
    >
      <template #actions>
        <el-button v-if="viewState === 'intro'" type="primary" round size="large" @click="startSession(selectedDuration)">
          开始标准测试
        </el-button>
        <el-button v-else round size="large" @click="resetTest">
          重新选择模式
        </el-button>
      </template>
    </PageHero>

    <section v-if="viewState === 'intro'" class="app-grid-2">
      <article class="surface-panel page-card section-stack">
        <div class="section-heading">
          <span class="eyebrow">How It Works</span>
          <h2>不是快测，而是更接近正式感的站内测评</h2>
          <p>新版本除了看单词，还会附带一条简短释义，并且整体题量明显增加。深度模式不会再几分钟提前结束，而是先做满一轮高强度题量，再决定是否继续确认边界。</p>
        </div>

        <div class="flow-list">
          <article class="flow-item">
            <strong>第一阶段</strong>
            <p>全局粗定位，先快速铺开你的大致区间。</p>
          </article>
          <article class="flow-item">
            <strong>第二阶段</strong>
            <p>围绕边界档位大范围加测，压缩误差。</p>
          </article>
          <article class="flow-item">
            <strong>第三阶段</strong>
            <p>专门负责最终确认，尤其是深度模式。</p>
          </article>
        </div>
      </article>

      <article class="surface-panel page-card section-stack">
        <div class="section-heading">
          <span class="eyebrow">Duration</span>
          <h2>选择测试时长</h2>
          <p>标准版默认推荐。三档都会比旧版本更重，结果仍然直接服务于你的默认 COCA 范围设置。</p>
        </div>

        <div class="duration-grid">
          <button
            v-for="option in durationOptions"
            :key="option.value"
            type="button"
            class="duration-card"
            :class="{ 'duration-card-active': selectedDuration === option.value }"
            @click="selectedDuration = option.value"
          >
            <span class="surface-tag">{{ option.time }}</span>
            <strong>{{ option.label }}</strong>
            <span class="duration-count">{{ option.questions }}</span>
            <p>{{ option.description }}</p>
          </button>
        </div>

        <div class="panel-actions">
          <el-button type="primary" round size="large" :loading="submitting" @click="startSession(selectedDuration)">
            开始 {{ selectedDurationLabel }}
          </el-button>
        </div>
      </article>
    </section>

    <section v-else-if="viewState === 'testing' && progress" class="test-layout">
      <article class="surface-panel page-card stage-panel">
        <div class="stage-top">
          <div class="section-heading compact-heading">
            <span class="eyebrow">Stage {{ progress.stage_number }}</span>
            <h2>{{ progress.stage_label }}</h2>
            <p>这轮测试会明显比旧版本更长。每个单词都带一条简短释义，请按你在真实阅读里是否能稳定理解来作答。</p>
          </div>

          <div class="stage-stats">
            <article class="meta-card">
              <span>当前阶段</span>
              <strong>{{ progress.stage_number }}/3</strong>
            </article>
            <article class="meta-card">
              <span>本阶段题量</span>
              <strong>{{ progress.questions.length }}</strong>
            </article>
            <article class="meta-card">
              <span>已作答</span>
              <strong>{{ answeredStageCount }}/{{ progress.questions.length }}</strong>
            </article>
            <article class="meta-card">
              <span>当前模式</span>
              <strong>{{ selectedDurationLabel }}</strong>
            </article>
          </div>
        </div>

        <el-progress
          :percentage="Math.round((answeredStageCount / Math.max(progress.questions.length, 1)) * 100)"
          :show-text="false"
          :stroke-width="10"
        />

        <div class="question-shell">
          <div class="question-header">
            <span class="surface-tag">第 {{ activeQuestionIndex + 1 }} 题 / {{ progress.questions.length }}</span>
            <span class="question-band">目标档位 COCA {{ activeQuestion.coca_band }}</span>
          </div>
          <div class="question-word">{{ activeQuestion.word }}</div>
          <div class="meaning-actions">
            <el-button
              round
              type="primary"
              plain
              @click="toggleMeaning(activeQuestion.question_id)"
            >
              {{ isMeaningVisible(activeQuestion.question_id) ? '隐藏释义' : '显示释义' }}
            </el-button>
          </div>
          <div v-if="isMeaningVisible(activeQuestion.question_id)" class="question-meaning">{{ activeQuestion.meaning }}</div>
          <p class="question-tip">判断标准不是“考试会不会拼写”，而是“阅读里看到它时，你大概率能直接明白”。</p>
        </div>

        <div class="answer-grid">
          <button
            v-for="option in answerOptions"
            :key="option.value"
            type="button"
            class="answer-card"
            :class="[
              `answer-card-${option.tone}`,
              { 'answer-card-active': stageAnswers[activeQuestion.question_id] === option.value }
            ]"
            @click="setAnswer(activeQuestion.question_id, option.value)"
          >
            <strong>{{ option.label }}</strong>
            <p>{{ option.description }}</p>
          </button>
        </div>

        <div class="question-dots">
          <button
            v-for="(question, index) in progress.questions"
            :key="question.question_id"
            type="button"
            class="question-dot"
            :class="[getQuestionDotClass(question.question_id), { 'question-dot-active': index === activeQuestionIndex }]"
            @click="activeQuestionIndex = index"
          >
            {{ index + 1 }}
          </button>
        </div>

        <div class="panel-actions split-actions">
          <div class="nav-actions">
            <el-button round :disabled="activeQuestionIndex === 0" @click="activeQuestionIndex -= 1">上一题</el-button>
            <el-button round :disabled="activeQuestionIndex >= progress.questions.length - 1" @click="activeQuestionIndex += 1">下一题</el-button>
          </div>
          <el-button type="primary" round :disabled="!allStageAnswered" :loading="submitting" @click="submitStage">
            提交本阶段
          </el-button>
        </div>
      </article>

      <aside class="section-stack">
        <article class="surface-panel page-card">
          <div class="section-heading compact-heading">
            <span class="eyebrow">Tips</span>
            <h3>作答建议</h3>
            <p>如果你只是模糊眼熟，但没法稳定理解，选“不确定”比勉强选“认识”更可靠。</p>
          </div>
          <div class="tip-list">
            <p>认识：看到就能大致明白。</p>
            <p>不认识：基本读不出来或读了也不懂。</p>
            <p>不确定：似曾相识，但把握不大。</p>
          </div>
        </article>

        <article class="surface-panel page-card">
          <div class="section-heading compact-heading">
            <span class="eyebrow">Current Mode</span>
            <h3>{{ selectedDurationLabel }}</h3>
            <p>{{ selectedDurationDescription }}</p>
          </div>
          <p class="mode-footnote">当前档位预计题量：{{ currentDurationOption.questions }}</p>
        </article>
      </aside>
    </section>

    <section v-else-if="viewState === 'result' && result" class="section-stack">
      <section class="app-grid-4">
        <MetricCard label="推荐档位" :value="result.recommended_coca_label" caption="建议用这个档位作为默认已掌握范围。" accent />
        <MetricCard label="预估词汇量" :value="`${formatNumber(result.estimated_vocabulary_size)} 词`" caption="连续估算值，用来补充离散档位判断。" />
        <MetricCard label="置信度" :value="result.confidence_label" :caption="`综合分 ${Math.round(result.confidence * 100)} / 100`" />
        <MetricCard label="作答量" :value="formatNumber(result.answered_count)" :caption="`其中 ${formatNumber(result.unsure_count)} 题选择了不确定`" />
      </section>

      <section class="app-grid-2">
        <article class="surface-panel page-card section-stack">
          <div class="section-heading">
            <span class="eyebrow">Recommendation</span>
            <h2>{{ result.summary }}</h2>
            <p>这是产品内估算，不等同于正式语言测评。它更适合用来决定分析书籍时的 COCA 默认范围。</p>
          </div>

          <div class="result-actions">
            <el-button type="primary" round size="large" @click="applyResult">
              设为默认词汇基础
            </el-button>
            <el-button round size="large" @click="resetTest">再测一次</el-button>
          </div>
        </article>

        <article class="surface-panel page-card section-stack">
          <div class="section-heading">
            <span class="eyebrow">Band Window</span>
            <h2>边界附近表现</h2>
            <p>这里展示和当前结果最相关的相邻档位表现，用来解释为什么系统把你落在这个区间。</p>
          </div>

          <div class="band-list">
            <article v-for="band in result.band_scores" :key="band.coca_band" class="band-item">
              <div class="band-copy">
                <strong>COCA {{ band.coca_band }}</strong>
                <span>{{ band.answered_count }} 题</span>
              </div>
              <div class="band-bar">
                <div class="band-bar-fill" :style="{ width: `${Math.round(band.score * 100)}%` }" />
              </div>
              <strong class="band-score">{{ Math.round(band.score * 100) }}%</strong>
            </article>
          </div>
        </article>
      </section>
    </section>

    <section v-else class="surface-panel page-card">
      <el-skeleton animated :rows="6" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

type DurationMode = 'quick' | 'standard' | 'deep'
type AnswerValue = 'know' | 'dont_know' | 'unsure'

type VocabularyTestQuestion = {
  question_id: string
  word: string
  meaning: string
  coca_rank: number
  coca_band: number
}

type VocabularyTestBandScore = {
  coca_band: number
  score: number
  answered_count: number
}

type VocabularyTestResult = {
  recommended_coca_rank: number
  recommended_coca_label: string
  estimated_vocabulary_size: number
  confidence: number
  confidence_label: string
  answered_count: number
  unsure_count: number
  band_scores: VocabularyTestBandScore[]
  summary: string
}

type VocabularyTestSessionResponse = {
  session_id: string
  completed: boolean
  stage_number: number
  stage_label: string
  questions: VocabularyTestQuestion[]
  result?: VocabularyTestResult | null
}

type ViewState = 'intro' | 'testing' | 'result' | 'loading'

const { request } = useApi()
const { setDefaultKnownWordsSelection } = useUserPreferences()
const { getKnownWordsLabel } = useKnownWordsOptions()

const durationOptions: Array<{
  value: DurationMode
  label: string
  time: string
  questions: string
  description: string
}> = [
  { value: 'quick', label: '短测版', time: '4-7 分钟', questions: '约 40-60 题', description: '适合先做一次较短测评，快速筛出你大致落在哪个区间。' },
  { value: 'standard', label: '标准版', time: '8-12 分钟', questions: '约 80-110 题', description: '默认推荐。题量已经明显上调，适合大多数人做更稳的边界判断。' },
  { value: 'deep', label: '深度版', time: '10-15 分钟', questions: '约 120-180 题', description: '高精度模式。题量最多，且不会在前两阶段过早结束。' }
]

const answerOptions: Array<{
  value: AnswerValue
  label: string
  description: string
  tone: 'positive' | 'neutral' | 'negative'
}> = [
  { value: 'know', label: '认识', description: '看到这个词，大概率能直接明白。', tone: 'positive' },
  { value: 'unsure', label: '不确定', description: '眼熟，但并不稳定，理解把握不大。', tone: 'neutral' },
  { value: 'dont_know', label: '不认识', description: '基本不懂，或看到时无法直接理解。', tone: 'negative' }
]

const viewState = ref<ViewState>('intro')
const selectedDuration = ref<DurationMode>('standard')
const progress = ref<VocabularyTestSessionResponse | null>(null)
const result = ref<VocabularyTestResult | null>(null)
const activeQuestionIndex = ref(0)
const stageAnswers = ref<Record<string, AnswerValue>>({})
const revealedMeanings = ref<Record<string, boolean>>({})
const submitting = ref(false)

const currentDurationOption = computed(() => (
  durationOptions.find((option) => option.value === selectedDuration.value) || durationOptions[1]
))
const selectedDurationLabel = computed(() => currentDurationOption.value.label)
const selectedDurationDescription = computed(() => currentDurationOption.value.description)
const answeredStageCount = computed(() => Object.keys(stageAnswers.value).length)
const allStageAnswered = computed(() => (
  !!progress.value
  && progress.value.questions.length > 0
  && progress.value.questions.every((question) => !!stageAnswers.value[question.question_id])
))
const activeQuestion = computed(() => {
  if (!progress.value?.questions.length) {
    return {
      question_id: '',
      word: '',
      meaning: '',
      coca_rank: 0,
      coca_band: 1000
    }
  }
  return progress.value.questions[activeQuestionIndex.value] || progress.value.questions[0]
})
const heroStats = computed(() => [
  { label: '当前模式', value: result.value?.recommended_coca_label || selectedDurationLabel.value },
  { label: '阶段状态', value: viewState.value === 'testing' ? `第 ${progress.value?.stage_number || 1} 阶段` : viewState.value === 'result' ? '已完成' : '等待开始' },
  { label: '推荐用途', value: result.value ? getKnownWordsLabel('coca_rank', String(result.value.recommended_coca_rank)) : '默认 COCA 范围' }
])

const formatNumber = (value: number) => new Intl.NumberFormat('zh-CN').format(value)

const resetTest = () => {
  viewState.value = 'intro'
  progress.value = null
  result.value = null
  activeQuestionIndex.value = 0
  stageAnswers.value = {}
  revealedMeanings.value = {}
}

const resetStageState = () => {
  activeQuestionIndex.value = 0
  stageAnswers.value = {}
  revealedMeanings.value = {}
}

const startSession = async (durationMode: DurationMode) => {
  submitting.value = true
  viewState.value = 'loading'
  try {
    const response = await request<VocabularyTestSessionResponse>('/vocab-test/sessions', {
      method: 'POST',
      body: {
        duration_mode: durationMode
      }
    })
    progress.value = response
    result.value = response.result || null
    resetStageState()
    viewState.value = response.completed ? 'result' : 'testing'
  } catch (error: any) {
    viewState.value = 'intro'
    ElMessage.error(error?.data?.message || error?.message || '测试创建失败')
  } finally {
    submitting.value = false
  }
}

const setAnswer = (questionId: string, value: AnswerValue) => {
  stageAnswers.value = {
    ...stageAnswers.value,
    [questionId]: value
  }
  if (!progress.value) {
    return
  }
  if (activeQuestionIndex.value < progress.value.questions.length - 1) {
    activeQuestionIndex.value += 1
  }
}

const isMeaningVisible = (questionId: string) => !!revealedMeanings.value[questionId]

const toggleMeaning = (questionId: string) => {
  revealedMeanings.value = {
    ...revealedMeanings.value,
    [questionId]: !revealedMeanings.value[questionId]
  }
}

const getQuestionDotClass = (questionId: string) => {
  const answer = stageAnswers.value[questionId]
  if (answer === 'know') {
    return 'question-dot-know'
  }
  if (answer === 'unsure') {
    return 'question-dot-unsure'
  }
  if (answer === 'dont_know') {
    return 'question-dot-dont-know'
  }
  return ''
}

const submitStage = async () => {
  if (!progress.value || !allStageAnswered.value) {
    return
  }
  submitting.value = true
  try {
    const response = await request<VocabularyTestSessionResponse>(`/vocab-test/sessions/${progress.value.session_id}/answers`, {
      method: 'POST',
      body: {
        answers: progress.value.questions.map((question) => ({
          question_id: question.question_id,
          response: stageAnswers.value[question.question_id]
        }))
      }
    })
    progress.value = response
    if (response.completed && response.result) {
      result.value = response.result
      viewState.value = 'result'
      ElMessage.success(`测试完成，推荐档位为 ${response.result.recommended_coca_label}`)
      return
    }
    resetStageState()
    viewState.value = 'testing'
    ElMessage.success(`已进入第 ${response.stage_number} 阶段`)
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '阶段提交失败')
  } finally {
    submitting.value = false
  }
}

const applyResult = () => {
  if (!result.value) {
    return
  }
  setDefaultKnownWordsSelection({
    mode: 'coca_rank',
    value: String(result.value.recommended_coca_rank)
  })
  ElMessage.success(`默认词汇基础已更新为 ${result.value.recommended_coca_label}`)
}
</script>

<style scoped>
.vocab-test-page,
.page-card,
.test-layout,
.stage-panel,
.flow-list,
.duration-grid,
.band-list {
  display: grid;
  gap: 20px;
}

.page-card {
  padding: 28px;
}

.flow-item,
.meta-card,
.band-item {
  display: grid;
  gap: 8px;
  padding: 18px 20px;
  border-radius: 22px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.flow-item p,
.meta-card span,
.question-tip,
.question-meaning,
.duration-card p,
.answer-card p,
.tip-list p,
.band-copy span,
.mode-footnote,
.duration-count {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.7;
}

.duration-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.duration-card,
.answer-card,
.question-dot {
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
  color: var(--text-main);
}

.duration-card,
.answer-card {
  display: grid;
  gap: 12px;
  width: 100%;
  padding: 22px;
  border-radius: 24px;
  text-align: left;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.duration-card strong,
.answer-card strong,
.question-word {
  color: var(--text-strong);
}

.duration-count {
  font-size: 13px;
  font-weight: 700;
}

.duration-card-active,
.answer-card-active {
  border-color: rgba(78, 123, 255, 0.36);
  box-shadow: 0 18px 36px rgba(78, 123, 255, 0.12);
  transform: translateY(-2px);
}

.panel-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.test-layout {
  grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
  align-items: start;
}

.stage-top,
.stage-stats {
  display: grid;
  gap: 16px;
}

.stage-stats {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.compact-heading {
  gap: 12px;
}

.meta-card span {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.meta-card strong {
  font-size: 28px;
  line-height: 1;
}

.question-shell {
  display: grid;
  gap: 14px;
  padding: 30px;
  border-radius: 28px;
  background: var(--surface-accent-soft);
  border: 1px solid var(--border-soft);
}

.question-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.question-band {
  color: var(--text-soft);
  font-weight: 700;
}

.question-word {
  font-size: clamp(44px, 7vw, 88px);
  line-height: 0.95;
  letter-spacing: -0.06em;
}

.meaning-actions {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.question-meaning {
  font-size: clamp(20px, 2.6vw, 28px);
  color: var(--text-main);
  font-weight: 700;
  white-space: pre-line;
}

.answer-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.answer-card-positive.answer-card-active {
  border-color: rgba(31, 185, 128, 0.38);
  box-shadow: 0 18px 36px rgba(31, 185, 128, 0.12);
}

.answer-card-neutral.answer-card-active {
  border-color: rgba(245, 166, 35, 0.36);
  box-shadow: 0 18px 36px rgba(245, 166, 35, 0.12);
}

.answer-card-negative.answer-card-active {
  border-color: rgba(225, 79, 92, 0.36);
  box-shadow: 0 18px 36px rgba(225, 79, 92, 0.12);
}

.question-dots {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.question-dot {
  min-width: 42px;
  min-height: 42px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
  color: var(--text-main);
}

.question-dot-know {
  border-color: rgba(31, 185, 128, 0.36);
  background: rgba(31, 185, 128, 0.12);
  color: var(--success-500);
}

.question-dot-unsure {
  border-color: rgba(245, 166, 35, 0.36);
  background: rgba(245, 166, 35, 0.12);
  color: var(--warning-500);
}

.question-dot-dont-know {
  border-color: rgba(225, 79, 92, 0.36);
  background: rgba(225, 79, 92, 0.12);
  color: var(--danger-500);
}

.question-dot-active {
  background: var(--primary-500);
  border-color: var(--primary-500);
  color: var(--text-inverse);
}

.question-dot-done {
  border-color: rgba(31, 185, 128, 0.36);
}

.split-actions {
  justify-content: space-between;
}

.nav-actions,
.result-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.tip-list {
  display: grid;
  gap: 10px;
}

.mode-footnote {
  padding: 14px 16px;
  border-radius: 18px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.band-list {
  gap: 16px;
}

.band-item {
  grid-template-columns: minmax(120px, auto) 1fr auto;
  align-items: center;
}

.band-copy {
  display: grid;
  gap: 6px;
}

.band-bar {
  position: relative;
  min-height: 14px;
  border-radius: 999px;
  background: rgba(126, 143, 177, 0.14);
  overflow: hidden;
}

.band-bar-fill {
  min-height: 14px;
  border-radius: 999px;
  background: var(--surface-accent);
}

.band-score {
  min-width: 60px;
  text-align: right;
}

@media (max-width: 1080px) {
  .test-layout,
  .app-grid-2,
  .duration-grid,
  .answer-grid,
  .stage-stats {
    grid-template-columns: 1fr;
  }

  .band-item {
    grid-template-columns: 1fr;
  }

  .split-actions {
    justify-content: flex-start;
  }
}
</style>
