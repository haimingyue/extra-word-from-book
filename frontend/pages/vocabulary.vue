<template>
  <div class="app-shell section-stack vocabulary-page">
    <AppNavigation />

    <PageHero
      eyebrow="Vocabulary"
      title="个人词库管理"
      description="导入已掌握词、手动补充词条，并在分析书籍时与考试标签或 COCA 档位做并集过滤。这里的重点是让管理过程更轻、更清楚。"
      :stats="heroStats"
    />

    <EmptyStateCard
      v-if="!isAuthenticated"
      eyebrow="Sign In"
      title="登录后管理你的词库"
      description="词库按用户隔离保存。登录后可以上传 TXT、搜索、筛选、手动新增和批量删除词条。"
    >
      <template #actions>
        <el-button type="primary" round @click="openAuth('login', loadVocabularies)">立即登录</el-button>
        <NuxtLink to="/">
          <el-button round>回到首页</el-button>
        </NuxtLink>
      </template>
    </EmptyStateCard>

    <template v-else>
      <section class="control-grid">
        <article class="surface-panel page-card action-panel">
          <div class="section-heading">
            <span class="eyebrow">TXT Import</span>
            <h2>上传已掌握词表</h2>
            <p>支持一行一个词，也支持现有 tab 分隔格式。上传成功后会自动同步到当前主词库。</p>
          </div>
          <button class="file-button" type="button" @click="triggerFileSelect">
            <span>{{ selectedFileName || '选择 TXT 文件' }}</span>
            <strong>{{ selectedFileName ? '已准备' : '点击选择' }}</strong>
          </button>
          <el-button type="primary" round :loading="uploading" @click="uploadVocabulary">
            同步到词库
          </el-button>
        </article>

        <article class="surface-panel page-card action-panel">
          <div class="section-heading">
            <span class="eyebrow">Manual Add</span>
            <h2>手动新增单词</h2>
            <p>适合补充少量已掌握词，录入后会立即写入当前激活的词库。</p>
          </div>
          <el-input
            v-model="newWord"
            size="large"
            placeholder="输入一个英文单词，如 therefore"
            @keyup.enter="createWord"
          />
          <el-button type="primary" round :loading="creating" @click="createWord">
            新增词条
          </el-button>
        </article>
      </section>

      <section class="surface-panel page-card list-panel">
        <div class="list-header">
          <div class="section-heading compact-heading">
            <span class="eyebrow">Items</span>
            <h2>{{ activeVocabulary?.name || '主词库' }}</h2>
            <p>筛选、搜索和批量操作都集中在这里，减少页面切换和控制噪声。</p>
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

        <div class="toolbar-grid">
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

          <div class="bulk-bar">
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
        </div>

        <div v-if="loading" class="surface-panel--soft loading-panel">
          <el-skeleton animated :rows="8" />
        </div>

        <div v-else-if="items.length" class="item-list">
          <article v-for="item in items" :key="item.item_id" class="item-row">
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
            <div class="item-actions">
              <span class="surface-tag">{{ activeVocabulary?.name || '主词库' }}</span>
              <el-button text type="danger" @click="deleteWord(item.item_id)">删除</el-button>
            </div>
          </article>
        </div>

        <div v-else class="empty-inline">
          <h3>当前筛选下没有单词</h3>
          <p>换一个搜索词、首字母，或者先上传一份 TXT / 手动新增词条。</p>
        </div>

        <div class="pagination-panel">
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
const { isAuthenticated, openAuth } = useAuth()

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
const heroStats = computed(() => [
  { label: '当前词条数', value: activeVocabulary.value?.item_count || 0 },
  { label: '筛选结果', value: total.value },
  { label: '已选词条', value: selectedItemIds.value.length }
])

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
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.action-panel,
.list-panel,
.compact-heading,
.pagination-copy,
.empty-inline {
  display: grid;
  gap: 16px;
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
  background: var(--surface-soft);
  color: var(--text-main);
  text-align: left;
}

.file-button strong {
  color: var(--primary-600);
  font-size: 14px;
}

.list-panel {
  gap: 20px;
}

.list-header,
.header-actions,
.filter-bar,
.bulk-bar,
.bulk-summary,
.item-row,
.item-actions,
.pagination-panel {
  display: flex;
  align-items: center;
  gap: 12px;
}

.list-header,
.bulk-bar,
.item-row,
.pagination-panel {
  justify-content: space-between;
}

.header-actions,
.filter-bar,
.bulk-summary {
  flex-wrap: wrap;
}

.toolbar-grid {
  display: grid;
  gap: 14px;
}

.filter-bar,
.bulk-bar,
.item-list,
.loading-panel,
.empty-inline {
  padding: 18px;
  border-radius: 22px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.filter-bar {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) 180px auto auto;
}

.bulk-select {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--text-main);
}

.item-list {
  display: grid;
  gap: 10px;
}

.item-row {
  padding: 14px 0;
  border-bottom: 1px solid var(--border-soft);
}

.item-row:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

.item-copy {
  display: grid;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.item-copy strong {
  font-size: 20px;
  line-height: 1;
}

.item-copy span,
.pagination-copy span,
.empty-inline p {
  color: var(--text-soft);
}

.item-actions {
  justify-content: flex-end;
}

.empty-inline h3,
.empty-inline p {
  margin: 0;
}

.pagination-copy strong {
  font-size: 18px;
}

.vocabulary-select,
.starts-with-select {
  width: 180px;
}

@media (max-width: 1100px) {
  .control-grid,
  .filter-bar {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .list-header,
  .bulk-bar,
  .item-row,
  .pagination-panel {
    align-items: flex-start;
    flex-direction: column;
  }

  .item-actions {
    width: 100%;
    justify-content: space-between;
  }
}

@media (max-width: 720px) {
  .file-button {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
