<template>
  <div class="history-page">
    <header class="history-topbar">
      <div class="topbar-left">
        <NuxtLink to="/" class="back-link soft-pill">返回首页</NuxtLink>
        <NuxtLink to="/vocabulary" class="back-link soft-pill">词库</NuxtLink>
        <button class="theme-toggle soft-pill" type="button" @click="toggleTheme">
          <span>{{ theme === 'light' ? '浅色' : '暗色' }}</span>
        </button>
      </div>

      <div class="topbar-right">
        <template v-if="isAuthenticated">
          <NuxtLink to="/profile" class="user-chip soft-pill">
            <span>{{ displayName }}</span>
          </NuxtLink>
          <el-button round @click="handleLogout">退出</el-button>
        </template>
        <template v-else>
          <el-button round @click="openAuth('login')">登录</el-button>
          <el-button type="primary" round @click="openAuth('register')">注册</el-button>
        </template>
      </div>
    </header>

    <section class="hero-panel soft-panel">
      <div>
        <span class="hero-kicker soft-pill">Bookshelf</span>
        <h1>书架与历史记录</h1>
        <p>查看你已经完成的词汇分析，快速回到结果页继续下载 CSV 或判断下一本书是否适合阅读。</p>
      </div>
      <div class="hero-meta">
        <div class="meta-block">
          <strong>{{ total }}</strong>
          <span>累计分析结果</span>
        </div>
        <div class="meta-block">
          <strong>{{ items.length }}</strong>
          <span>当前页记录</span>
        </div>
      </div>
    </section>

    <section v-if="!isAuthenticated" class="empty-panel soft-panel">
      <h2>登录后查看你的书架</h2>
      <p>历史记录按用户隔离保存。登录后可以查看你的分析结果、词汇负担和阅读建议。</p>
      <div class="empty-actions">
        <el-button type="primary" round @click="openAuth('login', loadHistory)">立即登录</el-button>
        <NuxtLink to="/">
          <el-button round>回到首页</el-button>
        </NuxtLink>
      </div>
    </section>

    <section v-else-if="loading" class="loading-panel soft-panel">
      <el-skeleton animated :rows="8" />
    </section>

    <section v-else-if="items.length" class="history-section">
      <div class="history-grid">
        <article v-for="item in items" :key="item.result_id" class="history-card soft-panel">
          <div class="card-top">
            <span class="file-chip soft-pill">{{ item.original_filename }}</span>
            <span class="status-badge" :class="statusClass(item.status)">{{ statusLabel(item.status) }}</span>
          </div>

          <div class="card-copy">
            <h2>{{ item.title || item.original_filename }}</h2>
            <p>{{ getKnownWordsLabel(item.known_words_level) }} 下，本书仍有 {{ formatNumber(item.to_memorize_word_count) }} 个待记忆词。</p>
          </div>

          <div class="card-metrics">
            <div>
              <strong>{{ formatNumber(item.to_memorize_word_count) }}</strong>
              <span>待记忆词数</span>
            </div>
            <div>
              <strong>{{ formatDate(item.created_at) }}</strong>
              <span>分析时间</span>
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

      <div class="pagination-row soft-panel">
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
      </div>
    </section>

    <section v-else class="empty-panel soft-panel">
      <h2>你的书架还是空的</h2>
      <p>先从首页上传一本英文 EPUB，完成分析后，这里会自动展示你的历史记录。</p>
      <NuxtLink to="/">
        <el-button type="primary" round>去首页开始分析</el-button>
      </NuxtLink>
    </section>

    <el-dialog
      v-model="reanalyzeVisible"
      width="520px"
      title="重新分析这本书"
      destroy-on-close
    >
      <div class="reanalyze-dialog">
        <p class="dialog-copy">
          复用已上传的 EPUB 文件，重新选择一个 COCA 已掌握范围，系统会基于你当前词库再次生成新的分析结果。
        </p>

        <div class="dialog-book soft-panel">
          <strong>{{ selectedHistoryItem?.title || selectedHistoryItem?.original_filename || '未选择书籍' }}</strong>
          <span>{{ selectedHistoryItem?.original_filename || '' }}</span>
        </div>

        <div class="dialog-field">
          <span class="field-label">已掌握范围</span>
          <el-select v-model="reanalyzeKnownWordsLevel" size="large" class="dialog-select">
            <el-option
              v-for="option in knownWordsOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
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
  known_words_level: number
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
const { theme, toggleTheme } = useTheme()
const { isAuthenticated, displayName, openAuth, clearAuth } = useAuth()
const { knownWordsOptions, getKnownWordsLabel } = useKnownWordsOptions()
const { defaultKnownWordsLevel } = useUserPreferences()

const loading = ref(false)
const items = ref<HistoryItem[]>([])
const total = ref(0)
const pageSize = 12
const reanalyzeVisible = ref(false)
const reanalyzeKnownWordsLevel = ref(defaultKnownWordsLevel.value)
const selectedHistoryItem = ref<HistoryItem | null>(null)
const reanalyzingBookId = ref<number | null>(null)
const deletingResultId = ref<number | null>(null)

const page = computed(() => {
  const rawPage = Number(route.query.page || 1)
  return Number.isFinite(rawPage) && rawPage > 0 ? rawPage : 1
})

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
  reanalyzeKnownWordsLevel.value = defaultKnownWordsLevel.value
  reanalyzeVisible.value = true
}

const submitReanalyze = async () => {
  if (!selectedHistoryItem.value) {
    return
  }

  reanalyzingBookId.value = selectedHistoryItem.value.book_id
  try {
    const job = await request<{
      job_id: number
      book_id: number
      status: string
      known_words_level: number
      result_id?: number | null
    }>('/analysis/jobs', {
      method: 'POST',
      body: {
        book_id: selectedHistoryItem.value.book_id,
        known_words_level: reanalyzeKnownWordsLevel.value
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

const handleLogout = async () => {
  clearAuth()
  items.value = []
  total.value = 0
  ElMessage.success('已退出登录')
  await router.push('/')
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
  width: min(1180px, 100%);
  margin: 0 auto;
  padding: 24px 20px 48px;
}

.history-topbar,
.topbar-left,
.topbar-right,
.hero-meta,
.card-top,
.card-actions,
.empty-actions,
.dialog-actions {
  display: flex;
  align-items: center;
}

.history-topbar {
  justify-content: space-between;
  gap: 20px;
}

.topbar-left,
.topbar-right,
.hero-meta,
.card-actions,
.empty-actions,
.dialog-actions {
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
.loading-panel,
.empty-panel,
.pagination-row {
  margin-top: 24px;
  padding: 28px;
}

.hero-panel {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.hero-kicker,
.file-chip {
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

.hero-panel h1 {
  margin: 18px 0 12px;
  font-size: clamp(40px, 5vw, 62px);
  line-height: 0.96;
  letter-spacing: -0.05em;
}

.hero-panel p,
.empty-panel p,
.card-copy p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.8;
}

.hero-meta {
  flex-wrap: wrap;
  align-items: stretch;
}

.meta-block {
  display: grid;
  gap: 8px;
  min-width: 140px;
  padding: 18px 20px;
  border-radius: var(--radius-sm);
  background: var(--surface-3);
  box-shadow: var(--shadow-inset);
}

.meta-block strong {
  font-size: 28px;
}

.meta-block span,
.card-metrics span,
.pagination-copy span {
  color: var(--text-soft);
}

.history-section {
  display: grid;
  gap: 20px;
  margin-top: 24px;
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

.card-top {
  justify-content: space-between;
  gap: 12px;
}

.status-badge {
  padding: 10px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status-completed {
  color: var(--accent-600);
  background: rgba(77, 201, 170, 0.14);
}

.status-processing,
.status-pending {
  color: var(--primary-600);
  background: rgba(58, 141, 255, 0.14);
}

.status-failed,
.status-canceled {
  color: var(--danger-500);
  background: rgba(255, 123, 123, 0.14);
}

.card-copy h2,
.empty-panel h2 {
  margin: 0 0 10px;
  font-size: 28px;
  line-height: 1.1;
}

.card-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.card-metrics div {
  display: grid;
  gap: 6px;
}

.card-metrics strong,
.pagination-copy strong {
  font-size: 18px;
}

.pagination-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.pagination-copy {
  display: grid;
  gap: 6px;
}

.reanalyze-dialog {
  display: grid;
  gap: 18px;
}

.dialog-copy {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.8;
}

.dialog-book {
  display: grid;
  gap: 6px;
  padding: 18px 20px;
}

.dialog-book strong {
  font-size: 18px;
}

.dialog-book span,
.field-label {
  color: var(--text-soft);
}

.dialog-field {
  display: grid;
  gap: 10px;
}

.field-label {
  font-size: 13px;
  font-weight: 600;
}

.dialog-select {
  width: 100%;
}

.dialog-actions {
  justify-content: flex-end;
}

@media (max-width: 1024px) {
  .hero-panel,
  .pagination-row {
    flex-direction: column;
    align-items: stretch;
  }

  .history-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .history-page {
    padding-inline: 14px;
  }

  .history-topbar,
  .topbar-left,
  .topbar-right,
  .hero-meta,
  .card-actions,
  .empty-actions {
    flex-wrap: wrap;
  }

  .hero-panel,
  .loading-panel,
  .empty-panel,
  .pagination-row,
  .history-card {
    padding: 20px;
  }

  .hero-panel h1 {
    font-size: 36px;
  }

  .card-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
