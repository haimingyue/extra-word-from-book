<template>
  <div class="vocabulary-page">
    <header class="page-topbar">
      <div class="topbar-left">
        <NuxtLink to="/" class="back-link soft-pill">返回首页</NuxtLink>
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
        <span class="hero-kicker soft-pill">Vocabulary</span>
        <h1>个人词库管理</h1>
        <p>导入你已经掌握的单词，或手动维护词条。后续分析书籍时，系统会自动把这些词与 COCA 范围做并集过滤。</p>
      </div>
      <div class="hero-metrics">
        <div class="metric-box">
          <strong>{{ activeVocabulary?.item_count || 0 }}</strong>
          <span>当前词条数</span>
        </div>
        <div class="metric-box">
          <strong>{{ total }}</strong>
          <span>筛选结果数</span>
        </div>
        <div class="metric-box">
          <strong>{{ selectedItemIds.length }}</strong>
          <span>已选词条</span>
        </div>
      </div>
    </section>

    <section v-if="!isAuthenticated" class="empty-panel soft-panel">
      <h2>登录后管理你的词库</h2>
      <p>词库按用户隔离保存。登录后可以上传 TXT、查看词条列表、手动新增、搜索和批量删除词条。</p>
      <div class="empty-actions">
        <el-button type="primary" round @click="openAuth('login', loadVocabularies)">立即登录</el-button>
        <NuxtLink to="/">
          <el-button round>回到首页</el-button>
        </NuxtLink>
      </div>
    </section>

    <template v-else>
      <section class="control-grid">
        <article class="control-card soft-panel">
          <div class="card-head">
            <div>
              <span class="section-label">TXT Import</span>
              <h2>上传已掌握词表</h2>
            </div>
            <span class="helper-text">支持一行一个词，或现有 tab 分隔格式。</span>
          </div>
          <button class="file-trigger" type="button" @click="triggerFileSelect">
            <span>{{ selectedFileName || '选择 TXT 文件' }}</span>
          </button>
          <div class="card-actions">
            <el-button type="primary" round :loading="uploading" @click="uploadVocabulary">
              同步到词库
            </el-button>
          </div>
        </article>

        <article class="control-card soft-panel">
          <div class="card-head">
            <div>
              <span class="section-label">Manual Add</span>
              <h2>手动新增单词</h2>
            </div>
            <span class="helper-text">适合补充少量已掌握词，实时写入当前词库。</span>
          </div>
          <el-input
            v-model="newWord"
            size="large"
            placeholder="输入一个英文单词，如 therefore"
            @keyup.enter="createWord"
          />
          <div class="card-actions">
            <el-button type="primary" round :loading="creating" @click="createWord">
              新增词条
            </el-button>
          </div>
        </article>
      </section>

      <section class="list-panel soft-panel">
        <div class="list-header">
          <div>
            <span class="section-label">Items</span>
            <h2>{{ activeVocabulary?.name || '主词库' }}</h2>
          </div>
          <div class="header-actions">
            <el-select
              v-if="vocabularies.length > 1"
              v-model="activeVocabularyId"
              size="large"
              class="vocabulary-select"
              @change="handleVocabularyChange"
            >
              <el-option
                v-for="vocabulary in vocabularies"
                :key="vocabulary.vocabulary_id"
                :label="vocabulary.name"
                :value="vocabulary.vocabulary_id"
              />
            </el-select>
            <el-button round :loading="loading" @click="loadItems">刷新</el-button>
          </div>
        </div>

        <div class="filter-bar">
          <el-input
            v-model="keyword"
            size="large"
            clearable
            placeholder="搜索单词，如 there"
            @keyup.enter="applyFilters"
            @clear="applyFilters"
          />
          <el-select
            v-model="startsWith"
            size="large"
            clearable
            placeholder="首字母"
            class="starts-with-select"
            @change="applyFilters"
          >
            <el-option
              v-for="letter in alphabet"
              :key="letter"
              :label="letter.toUpperCase()"
              :value="letter"
            />
          </el-select>
          <el-button type="primary" round @click="applyFilters">搜索</el-button>
          <el-button round @click="resetFilters">清空筛选</el-button>
        </div>

        <div class="bulk-bar soft-panel">
          <label class="bulk-select">
            <input
              type="checkbox"
              :checked="isAllVisibleSelected"
              @change="toggleSelectAll"
            >
            <span>本页全选</span>
          </label>
          <div class="bulk-summary">
            <span>已选 {{ selectedItemIds.length }} 个词条</span>
            <el-button
              type="danger"
              round
              plain
              :disabled="!selectedItemIds.length"
              :loading="batchDeleting"
              @click="deleteSelected"
            >
              批量删除
            </el-button>
          </div>
        </div>

        <div v-if="loading" class="loading-panel">
          <el-skeleton animated :rows="8" />
        </div>

        <div v-else-if="items.length" class="item-grid">
          <article v-for="item in items" :key="item.item_id" class="item-card soft-panel">
            <label class="item-check">
              <input
                type="checkbox"
                :checked="selectedItemIds.includes(item.item_id)"
                @change="toggleItemSelection(item.item_id)"
              >
            </label>
            <div class="item-copy">
              <strong>{{ item.word }}</strong>
              <span>{{ item.lemma || '无原型信息' }}</span>
            </div>
            <el-button text type="danger" @click="deleteWord(item.item_id)">删除</el-button>
          </article>
        </div>

        <div v-else class="empty-items">
          <h3>当前筛选下没有单词</h3>
          <p>换一个搜索词、首字母，或者先上传一份 TXT / 手动新增词条。</p>
        </div>

        <div class="pagination-row">
          <div class="pagination-copy">
            <strong>第 {{ page }} 页</strong>
            <span>共 {{ total }} 条词条</span>
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
    </template>

    <input ref="fileInputRef" type="file" accept=".txt" hidden @change="onFileSelected">
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'

type VocabularyListItem = {
  vocabulary_id: number
  name: string
  is_primary: boolean
  item_count: number
  created_at: string
}

type VocabularyListResponse = {
  items: VocabularyListItem[]
}

type VocabularyItem = {
  item_id: number
  word: string
  lemma?: string | null
}

type VocabularyItemsResponse = {
  items: VocabularyItem[]
  total: number
  page: number
  page_size: number
}

const router = useRouter()
const route = useRoute()
const { request } = useApi()
const { theme, toggleTheme } = useTheme()
const { isAuthenticated, displayName, openAuth, clearAuth } = useAuth()

const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const newWord = ref('')
const keyword = ref('')
const startsWith = ref('')
const loading = ref(false)
const uploading = ref(false)
const creating = ref(false)
const batchDeleting = ref(false)
const vocabularies = ref<VocabularyListItem[]>([])
const activeVocabularyId = ref<number | null>(null)
const items = ref<VocabularyItem[]>([])
const selectedItemIds = ref<number[]>([])
const total = ref(0)
const pageSize = 20
const alphabet = 'abcdefghijklmnopqrstuvwxyz'.split('')

const selectedFileName = computed(() => selectedFile.value?.name || '')
const activeVocabulary = computed(() =>
  vocabularies.value.find((item) => item.vocabulary_id === activeVocabularyId.value) || null
)
const page = computed(() => {
  const raw = Number(route.query.page || 1)
  return Number.isFinite(raw) && raw > 0 ? raw : 1
})
const isAllVisibleSelected = computed(() =>
  items.value.length > 0 && items.value.every((item) => selectedItemIds.value.includes(item.item_id))
)

const triggerFileSelect = () => {
  fileInputRef.value?.click()
}

const onFileSelected = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) {
    return
  }
  selectedFile.value = file
  ElMessage.success(`已准备词库文件：${file.name}`)
}

const buildItemsPath = () => {
  if (!activeVocabularyId.value) {
    return ''
  }

  const query = new URLSearchParams({
    page: String(page.value),
    page_size: String(pageSize)
  })

  if (keyword.value.trim()) {
    query.set('keyword', keyword.value.trim())
  }

  if (startsWith.value) {
    query.set('starts_with', startsWith.value)
  }

  return `/vocabularies/${activeVocabularyId.value}/items?${query.toString()}`
}

const loadVocabularies = async () => {
  if (!isAuthenticated.value) {
    return
  }

  try {
    const response = await request<VocabularyListResponse>('/vocabularies')
    vocabularies.value = response.items
    if (!activeVocabularyId.value) {
      activeVocabularyId.value = response.items[0]?.vocabulary_id || null
    }
    if (activeVocabularyId.value) {
      await loadItems()
    } else {
      items.value = []
      total.value = 0
      selectedItemIds.value = []
    }
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '词库列表加载失败')
  }
}

const loadItems = async () => {
  const path = buildItemsPath()
  if (!isAuthenticated.value || !path) {
    items.value = []
    total.value = 0
    selectedItemIds.value = []
    return
  }

  loading.value = true
  try {
    const response = await request<VocabularyItemsResponse>(path)
    items.value = response.items
    total.value = response.total
    selectedItemIds.value = selectedItemIds.value.filter((itemId) =>
      response.items.some((item) => item.item_id === itemId)
    )
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '词条列表加载失败')
  } finally {
    loading.value = false
  }
}

const uploadVocabulary = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择 TXT 文件')
    return
  }

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    const response = await request<{
      vocabulary_id: number
      name: string
      imported_count: number
      deduplicated_count: number
    }>('/vocabularies/upload', {
      method: 'POST',
      body: formData
    })
    selectedFile.value = null
    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }
    ElMessage.success(`词库已同步：新增 ${response.imported_count} 个词`)
    activeVocabularyId.value = response.vocabulary_id
    await loadVocabularies()
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '词库上传失败')
  } finally {
    uploading.value = false
  }
}

const createWord = async () => {
  if (!newWord.value.trim()) {
    ElMessage.warning('请输入单词')
    return
  }

  creating.value = true
  try {
    const response = await request<{ item_id: number; created: boolean }>('/vocabularies/items', {
      method: 'POST',
      body: {
        vocabulary_id: activeVocabularyId.value,
        word: newWord.value
      }
    })
    ElMessage.success(response.created ? '词条已新增' : '词条已存在')
    newWord.value = ''
    await loadVocabularies()
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '新增失败')
  } finally {
    creating.value = false
  }
}

const deleteWord = async (itemId: number) => {
  try {
    await request<{ item_id: number; deleted: boolean }>(`/vocabularies/items/${itemId}`, {
      method: 'DELETE'
    })
    ElMessage.success('词条已删除')
    await loadVocabularies()
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '删除失败')
  }
}

const deleteSelected = async () => {
  if (!selectedItemIds.value.length) {
    return
  }

  await ElMessageBox.confirm(
    `确认删除已选中的 ${selectedItemIds.value.length} 个词条吗？`,
    '批量删除',
    {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消'
    }
  )

  batchDeleting.value = true
  try {
    const response = await request<{ deleted_count: number }>('/vocabularies/items/batch-delete', {
      method: 'POST',
      body: {
        item_ids: selectedItemIds.value
      }
    })
    ElMessage.success(`已删除 ${response.deleted_count} 个词条`)
    selectedItemIds.value = []
    await loadVocabularies()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.data?.message || error?.message || '批量删除失败')
    }
  } finally {
    batchDeleting.value = false
  }
}

const toggleItemSelection = (itemId: number) => {
  if (selectedItemIds.value.includes(itemId)) {
    selectedItemIds.value = selectedItemIds.value.filter((id) => id !== itemId)
    return
  }
  selectedItemIds.value = [...selectedItemIds.value, itemId]
}

const toggleSelectAll = () => {
  if (isAllVisibleSelected.value) {
    selectedItemIds.value = []
    return
  }
  selectedItemIds.value = items.value.map((item) => item.item_id)
}

const applyFilters = async () => {
  selectedItemIds.value = []
  await router.push({
    path: '/vocabulary',
    query: {
      ...(keyword.value.trim() ? { keyword: keyword.value.trim() } : {}),
      ...(startsWith.value ? { startsWith: startsWith.value } : {})
    }
  })
}

const resetFilters = async () => {
  keyword.value = ''
  startsWith.value = ''
  selectedItemIds.value = []
  await router.push({ path: '/vocabulary', query: {} })
}

const handlePageChange = async (nextPage: number) => {
  await router.push({
    path: '/vocabulary',
    query: {
      ...(nextPage > 1 ? { page: String(nextPage) } : {}),
      ...(keyword.value.trim() ? { keyword: keyword.value.trim() } : {}),
      ...(startsWith.value ? { startsWith: startsWith.value } : {})
    }
  })
}

const handleVocabularyChange = async () => {
  selectedItemIds.value = []
  await router.push({
    path: '/vocabulary',
    query: {
      ...(keyword.value.trim() ? { keyword: keyword.value.trim() } : {}),
      ...(startsWith.value ? { startsWith: startsWith.value } : {})
    }
  })
}

const handleLogout = async () => {
  clearAuth()
  vocabularies.value = []
  items.value = []
  total.value = 0
  selectedItemIds.value = []
  ElMessage.success('已退出登录')
  await router.push('/')
}

watch(
  () => route.query,
  async (query) => {
    keyword.value = typeof query.keyword === 'string' ? query.keyword : ''
    startsWith.value = typeof query.startsWith === 'string' ? query.startsWith : ''
  },
  { immediate: true }
)

watch(
  [() => isAuthenticated.value, () => page.value, () => activeVocabularyId.value, () => keyword.value, () => startsWith.value],
  async ([authenticated, currentPage, vocabularyId]) => {
    if (!authenticated) {
      vocabularies.value = []
      items.value = []
      total.value = 0
      selectedItemIds.value = []
      return
    }

    if (!vocabularies.value.length) {
      await loadVocabularies()
      return
    }

    if (vocabularyId && currentPage >= 1) {
      await loadItems()
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.vocabulary-page {
  min-height: 100vh;
  width: min(1180px, 100%);
  margin: 0 auto;
  padding: 24px 20px 48px;
}

.page-topbar,
.topbar-left,
.topbar-right,
.hero-panel,
.hero-metrics,
.control-grid,
.card-actions,
.list-header,
.header-actions,
.pagination-row,
.empty-actions,
.filter-bar,
.bulk-bar,
.bulk-summary,
.item-card {
  display: flex;
  align-items: center;
}

.page-topbar,
.list-header,
.pagination-row,
.bulk-bar,
.item-card {
  justify-content: space-between;
}

.topbar-left,
.topbar-right,
.hero-metrics,
.card-actions,
.header-actions,
.empty-actions,
.filter-bar,
.bulk-summary {
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
.control-card,
.list-panel,
.empty-panel,
.bulk-bar {
  padding: 28px;
}

.hero-panel,
.control-grid,
.list-panel,
.empty-panel {
  margin-top: 24px;
}

.hero-panel {
  justify-content: space-between;
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

.hero-copy h1 {
  margin: 18px 0 12px;
  font-size: clamp(40px, 5vw, 62px);
  line-height: 0.96;
  letter-spacing: -0.05em;
}

.hero-copy p,
.empty-panel p,
.helper-text,
.empty-items p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.8;
}

.hero-metrics {
  align-items: stretch;
  flex-wrap: wrap;
}

.metric-box {
  display: grid;
  gap: 8px;
  min-width: 140px;
  padding: 18px 20px;
  border-radius: var(--radius-sm);
  background: var(--surface-3);
  box-shadow: var(--shadow-inset);
}

.metric-box strong {
  font-size: 28px;
}

.metric-box span,
.item-copy span,
.pagination-copy span,
.bulk-summary span,
.bulk-select span {
  color: var(--text-soft);
}

.control-grid {
  gap: 18px;
  align-items: stretch;
}

.control-card {
  flex: 1;
  display: grid;
  gap: 18px;
}

.card-head {
  display: grid;
  gap: 10px;
}

.card-head h2,
.list-header h2,
.empty-panel h2,
.empty-items h3 {
  margin: 8px 0 0;
  font-size: 28px;
  line-height: 1.1;
}

.file-trigger {
  width: 100%;
  padding: 18px 20px;
  border: 1px dashed var(--border-strong);
  border-radius: 22px;
  background: var(--surface-3);
  color: var(--text-main);
  text-align: left;
  box-shadow: var(--shadow-inset);
  cursor: pointer;
}

.list-panel {
  display: grid;
  gap: 20px;
}

.vocabulary-select {
  min-width: 220px;
}

.filter-bar {
  flex-wrap: wrap;
}

.filter-bar :deep(.el-input),
.filter-bar :deep(.el-select) {
  flex: 1;
  min-width: 180px;
}

.starts-with-select {
  max-width: 140px;
}

.bulk-bar {
  padding: 18px 20px;
  border-radius: var(--radius-md);
  background: var(--surface-3);
  box-shadow: var(--shadow-inset);
}

.bulk-select {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.bulk-select input,
.item-check input {
  width: 18px;
  height: 18px;
  accent-color: var(--primary-500);
}

.item-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.item-card {
  gap: 14px;
  padding: 18px 20px;
}

.item-check {
  display: inline-flex;
  align-items: center;
}

.item-copy {
  display: grid;
  gap: 6px;
  flex: 1;
}

.item-copy strong,
.pagination-copy strong {
  font-size: 18px;
}

.loading-panel,
.empty-items {
  padding: 8px 0;
}

.pagination-copy {
  display: grid;
  gap: 6px;
}

@media (max-width: 1024px) {
  .hero-panel,
  .page-topbar,
  .list-header,
  .pagination-row,
  .control-grid,
  .bulk-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .item-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .vocabulary-page {
    padding-inline: 14px;
  }

  .topbar-left,
  .topbar-right,
  .hero-metrics,
  .header-actions,
  .empty-actions,
  .filter-bar,
  .bulk-summary {
    flex-wrap: wrap;
  }

  .hero-panel,
  .control-card,
  .list-panel,
  .empty-panel {
    padding: 20px;
  }

  .hero-copy h1 {
    font-size: 36px;
  }

  .vocabulary-select,
  .starts-with-select {
    width: 100%;
    min-width: 0;
    max-width: none;
  }
}
</style>
