<template>
  <div class="app-shell section-stack history-page">
    <AppNavigation />

    <PageHero
      eyebrow="Bookshelf"
      title="书架与分析历史"
      description="你的每次词汇分析都会留在这里。可以回看结果、重新分析同一本书，或者直接清理不再需要的记录。"
      :stats="heroStats"
    />

    <EmptyStateCard
      v-if="!isAuthenticated"
      eyebrow="Sign In"
      title="登录后查看你的书架"
      description="历史记录按用户隔离保存。登录后可以查看分析结果、阅读建议和 CSV 下载入口。"
    >
      <template #actions>
        <el-button type="primary" round @click="openAuth('login', loadHistory)">立即登录</el-button>
        <NuxtLink to="/">
          <el-button round>回到首页</el-button>
        </NuxtLink>
      </template>
    </EmptyStateCard>

    <section v-else-if="loading" class="surface-panel page-card">
      <el-skeleton animated :rows="8" />
    </section>

    <section v-else-if="items.length" class="section-stack">
      <div class="history-grid">
        <article v-for="item in items" :key="item.result_id" class="history-card surface-panel">
          <div class="card-top">
            <div class="card-badges">
              <span class="surface-tag">{{ item.original_filename }}</span>
              <span class="status-badge" :class="statusClass(item.status)">{{ statusLabel(item.status) }}</span>
            </div>
            <div class="card-date">{{ formatDate(item.created_at) }}</div>
          </div>

          <div class="card-main">
            <div class="card-copy">
              <h2>{{ item.title || item.original_filename }}</h2>
              <p>{{ getKnownWordsLabel(item.known_words_mode, item.known_words_value) }} 下，本书仍有 {{ formatNumber(item.to_memorize_word_count) }} 个待记忆词。</p>
            </div>

            <div class="card-metrics">
              <article class="metric-chip">
                <span>待记忆词</span>
                <strong>{{ formatNumber(item.to_memorize_word_count) }}</strong>
              </article>
              <article class="metric-chip">
                <span>分析状态</span>
                <strong>{{ statusLabel(item.status) }}</strong>
              </article>
            </div>
          </div>

          <div class="card-actions">
            <NuxtLink
              :to="{
                path: '/report',
                query: { resultId: String(item.result_id) }
              }"
            >
              <el-button type="primary" round>查看结果</el-button>
            </NuxtLink>
            <el-button
              round
              :loading="reanalyzingBookId === item.book_id"
              @click="openReanalyze(item)"
            >
              重新分析
            </el-button>
            <el-button
              text
              type="danger"
              :loading="deletingResultId === item.result_id"
              @click="deleteHistory(item)"
            >
              删除记录
            </el-button>
          </div>
        </article>
      </div>

      <section class="surface-panel page-card pagination-panel">
        <div class="pagination-copy">
          <strong>第 {{ page }} 页</strong>
          <span>共 {{ total }} 条历史记录</span>
        </div>
        <el-pagination
          background
          layout="prev, pager, next"
          :current-page="page"
          :page-size="pageSize"
          :total="total"
          @current-change="handlePageChange"
        />
      </section>
    </section>

    <EmptyStateCard
      v-else
      eyebrow="No History"
      title="你的书架还是空的"
      description="先从首页上传一本英文 EPUB，分析完成后，这里会自动展示历史结果。"
    >
      <template #actions>
        <NuxtLink to="/">
          <el-button type="primary" round>去首页开始分析</el-button>
        </NuxtLink>
      </template>
    </EmptyStateCard>

    <el-dialog
      v-model="reanalyzeVisible"
      width="520px"
      title="重新分析这本书"
      destroy-on-close
    >
      <div class="reanalyze-dialog">
        <p class="muted-copy">
          复用已上传的 EPUB 文件，重新选择一个考试标签或 COCA 档位，系统会基于你当前词库再次生成新的分析结果。
        </p>

        <div class="dialog-book">
          <strong>{{ selectedHistoryItem?.title || selectedHistoryItem?.original_filename || '未选择书籍' }}</strong>
          <span>{{ selectedHistoryItem?.original_filename || '' }}</span>
        </div>

        <div class="dialog-field">
          <span class="field-label">已掌握范围</span>
          <el-select v-model="reanalyzeKnownWordsOptionKey" size="large" class="dialog-select">
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
      </div>

      <template #footer>
        <div class="dialog-actions">
          <el-button round @click="reanalyzeVisible = false">取消</el-button>
          <el-button
            type="primary"
            round
            :loading="reanalyzingBookId !== null"
            @click="submitReanalyze"
          >
            开始重新分析
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'

type HistoryItem = {
  result_id: number
  job_id: number
  book_id: number
  title?: string | null
  original_filename: string
  status: string
  known_words_mode: 'exam_level' | 'coca_rank'
  known_words_value: string
  to_memorize_word_count: number
  created_at: string
}

type BookHistoryResponse = {
  items: HistoryItem[]
  total: number
  page: number
  page_size: number
}

const router = useRouter()
const route = useRoute()
const { request } = useApi()
const { isAuthenticated, openAuth } = useAuth()
const { knownWordsOptionGroups, getKnownWordsLabel, getKnownWordsOptionKey, parseKnownWordsOptionKey } = useKnownWordsOptions()
const { defaultKnownWordsSelection } = useUserPreferences()

const loading = ref(false)
const items = ref<HistoryItem[]>([])
const total = ref(0)
const pageSize = 12
const reanalyzeVisible = ref(false)
const reanalyzeKnownWordsOptionKey = ref(getKnownWordsOptionKey(defaultKnownWordsSelection.value))
const selectedHistoryItem = ref<HistoryItem | null>(null)
const reanalyzingBookId = ref<number | null>(null)
const deletingResultId = ref<number | null>(null)

const page = computed(() => {
  const rawPage = Number(route.query.page || 1)
  return Number.isFinite(rawPage) && rawPage > 0 ? rawPage : 1
})

const heroStats = computed(() => [
  { label: '累计结果', value: total.value },
  { label: '当前页记录', value: items.value.length },
  { label: '登录状态', value: isAuthenticated.value ? '已登录' : '未登录' }
])

const formatNumber = (value: number) => new Intl.NumberFormat('zh-CN').format(value)
const formatDate = (value: string) => new Date(value).toLocaleString('zh-CN')

const statusClass = (status: string) => `status-${status}`

const statusLabel = (status: string) => {
  if (status === 'completed') return '已完成'
  if (status === 'processing') return '分析中'
  if (status === 'pending') return '排队中'
  if (status === 'failed') return '失败'
  if (status === 'canceled') return '已取消'
  return status
}

const loadHistory = async () => {
  if (!isAuthenticated.value) {
    return
  }

  loading.value = true
  try {
    const response = await request<BookHistoryResponse>(`/books/history?page=${page.value}&page_size=${pageSize}`)
    items.value = response.items
    total.value = response.total
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '历史记录加载失败')
  } finally {
    loading.value = false
  }
}

const openReanalyze = (item: HistoryItem) => {
  selectedHistoryItem.value = item
  reanalyzeKnownWordsOptionKey.value = getKnownWordsOptionKey(defaultKnownWordsSelection.value)
  reanalyzeVisible.value = true
}

const submitReanalyze = async () => {
  if (!selectedHistoryItem.value) {
    return
  }

  reanalyzingBookId.value = selectedHistoryItem.value.book_id
  try {
    const reanalyzeSelection = parseKnownWordsOptionKey(reanalyzeKnownWordsOptionKey.value)
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
        book_id: selectedHistoryItem.value.book_id,
        known_words_mode: reanalyzeSelection.mode,
        known_words_value: reanalyzeSelection.value
      }
    })

    reanalyzeVisible.value = false
    ElMessage.success('已重新生成分析结果')

    await router.push({
      path: '/report',
      query: { jobId: String(job.job_id) }
    })
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '重新分析失败')
  } finally {
    reanalyzingBookId.value = null
  }
}

const deleteHistory = async (item: HistoryItem) => {
  try {
    await ElMessageBox.confirm(
      `确认删除《${item.title || item.original_filename}》这条分析记录吗？删除后对应结果和 CSV 文件将一并清理。`,
      '删除历史记录',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消'
      }
    )

    deletingResultId.value = item.result_id
    await request<{ result_id: number; deleted: boolean }>(`/books/history/${item.result_id}`, {
      method: 'DELETE'
    })
    ElMessage.success('历史记录已删除')

    if (items.value.length === 1 && page.value > 1) {
      await router.push({
        path: '/history',
        query: { page: String(page.value - 1) }
      })
      return
    }

    await loadHistory()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.data?.message || error?.message || '删除失败')
    }
  } finally {
    deletingResultId.value = null
  }
}

const handlePageChange = async (nextPage: number) => {
  await router.push({
    path: '/history',
    query: nextPage > 1 ? { page: String(nextPage) } : {}
  })
}

watch(
  [() => isAuthenticated.value, () => page.value],
  async ([authenticated]) => {
    if (!authenticated) {
      items.value = []
      total.value = 0
      return
    }
    await loadHistory()
  },
  { immediate: true }
)
</script>

<style scoped>
.history-page {
  min-height: 100vh;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.history-card {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.card-top,
.card-badges,
.card-actions,
.dialog-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.card-top {
  justify-content: space-between;
}

.card-date {
  color: var(--text-faint);
  font-size: 13px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.status-completed {
  color: var(--success-500);
  background: rgba(31, 185, 128, 0.12);
}

.status-processing,
.status-pending {
  color: var(--primary-600);
  background: rgba(78, 123, 255, 0.12);
}

.status-failed,
.status-canceled {
  color: var(--danger-500);
  background: rgba(225, 79, 92, 0.12);
}

.card-main {
  display: grid;
  gap: 18px;
}

.card-copy {
  display: grid;
  gap: 10px;
}

.card-copy h2 {
  margin: 0;
  font-size: 30px;
  line-height: 1;
}

.card-copy p,
.dialog-book span,
.field-label {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.75;
}

.card-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.metric-chip,
.dialog-book {
  display: grid;
  gap: 8px;
  padding: 18px;
  border-radius: 20px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.metric-chip span,
.field-label {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.metric-chip strong,
.pagination-copy strong,
.dialog-book strong {
  font-size: 20px;
  line-height: 1.05;
}

.card-actions {
  justify-content: flex-start;
}

.pagination-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.pagination-copy {
  display: grid;
  gap: 6px;
}

.pagination-copy span {
  color: var(--text-soft);
}

.reanalyze-dialog {
  display: grid;
  gap: 18px;
}

.dialog-select {
  width: 100%;
}

@media (max-width: 980px) {
  .history-grid,
  .card-metrics,
  .pagination-panel {
    grid-template-columns: 1fr;
    display: grid;
  }
}

@media (max-width: 720px) {
  .history-card {
    padding: 20px;
  }

  .card-copy h2 {
    font-size: 24px;
  }
}
</style>
