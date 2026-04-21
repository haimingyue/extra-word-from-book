<template>
  <section class="surface-panel page-card distribution-card">
    <div class="distribution-head">
      <div class="section-heading">
        <span class="eyebrow">Word Curve</span>
        <h3>词汇分布曲线</h3>
        <p>横轴为 COCA 分档，纵轴为该档位单词在本书中的累计出现次数。</p>
      </div>
      <p class="distribution-note">灰色/未知档表示没有匹配到 COCA 排名的词。</p>
    </div>

    <div v-if="loading" class="distribution-state">
      <el-skeleton animated :rows="5" />
    </div>

    <div v-else-if="errorMessage" class="distribution-state distribution-error">
      <strong>词汇分布加载失败</strong>
      <p>{{ errorMessage }}</p>
    </div>

    <div v-else>
      <div ref="chartRef" class="distribution-chart"></div>
      <p class="distribution-footnote">
        {{ footnote }}
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

type DistributionBucket = {
  key: string
  label: string
  token_count: number
  token_ratio: number
}

type DistributionResponse = {
  buckets: DistributionBucket[]
  known_words_mode: 'exam_level' | 'coca_rank'
  known_words_value: string
  total_word_count: number
}

const props = defineProps<{
  resultId: number
}>()

const { request } = useApi()
const chartRef = ref<HTMLDivElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const distribution = ref<DistributionResponse | null>(null)

const knownWordsLineIndex = computed(() => {
  if (!distribution.value || distribution.value.known_words_mode !== 'coca_rank') {
    return -1
  }

  const threshold = Number(distribution.value.known_words_value)
  if (!Number.isFinite(threshold) || threshold <= 0) {
    return -1
  }

  return distribution.value.buckets.findIndex((bucket) => {
    if (bucket.key === 'unknown') {
      return false
    }

    const [minText, maxText] = bucket.label.split('-')
    const minValue = Number(minText)
    if (bucket.label.endsWith('+')) {
      const lowerBound = Number(bucket.label.replace('+', ''))
      return threshold >= lowerBound
    }
    const maxValue = Number(maxText)
    return Number.isFinite(minValue) && Number.isFinite(maxValue) && threshold >= minValue && threshold <= maxValue
  })
})

const knownWordsCoverageRatio = computed(() => {
  if (!distribution.value || knownWordsLineIndex.value < 0 || distribution.value.total_word_count <= 0) {
    return null
  }

  const coveredTokenCount = distribution.value.buckets
    .slice(0, knownWordsLineIndex.value + 1)
    .reduce((sum, bucket) => sum + bucket.token_count, 0)

  return coveredTokenCount / distribution.value.total_word_count
})

const footnote = computed(() => {
  if (!distribution.value) {
    return ''
  }

  if (distribution.value.known_words_mode === 'coca_rank') {
    const coverageText = knownWordsCoverageRatio.value === null
      ? ''
      : `，覆盖 ${(knownWordsCoverageRatio.value * 100).toFixed(2)}%`
    return `虚线表示当前已掌握范围：COCA ${distribution.value.known_words_value}${coverageText}。`
  }
  return '当前已掌握范围为考试词表模式，本图不展示 COCA 阈值线。'
})

const renderChart = () => {
  if (!chartRef.value || !distribution.value) {
    return
  }

  if (!chart.value) {
    chart.value = echarts.init(chartRef.value)
  }

  const labels = distribution.value.buckets.map((bucket) => bucket.label)
  const counts = distribution.value.buckets.map((bucket) => bucket.token_count)
  const markLineIndex = knownWordsLineIndex.value

  chart.value.setOption({
    animationDuration: 600,
    color: ['#4e7bff'],
    grid: {
      left: 24,
      right: 24,
      top: 36,
      bottom: 30,
      containLabel: true
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(24, 32, 51, 0.92)',
      borderWidth: 0,
      textStyle: {
        color: '#fff9f5'
      },
      formatter: (params: any) => {
        const point = Array.isArray(params) ? params[0] : params
        const bucket = distribution.value?.buckets[point.dataIndex]
        if (!bucket) {
          return ''
        }
        const cumulativeRatio = distribution.value?.buckets
          .slice(0, point.dataIndex + 1)
          .reduce((sum, currentBucket) => sum + currentBucket.token_ratio, 0) ?? 0
        return [
          `${bucket.label}`,
          `累计出现次数：${new Intl.NumberFormat('zh-CN').format(bucket.token_count)}`,
          `占全书比例：${(bucket.token_ratio * 100).toFixed(2)}%`,
          `累计掌握全书：${(cumulativeRatio * 100).toFixed(2)}%`
        ].join('<br/>')
      }
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisLine: {
        lineStyle: {
          color: 'rgba(126, 143, 177, 0.32)'
        }
      },
      axisLabel: {
        color: '#69758d',
        interval: 0,
        rotate: 24
      }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLine: {
        show: false
      },
      axisLabel: {
        color: '#69758d'
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(126, 143, 177, 0.12)'
        }
      }
    },
    series: [
      {
        name: '词频分布',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: counts,
        lineStyle: {
          width: 3
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(78, 123, 255, 0.32)' },
            { offset: 1, color: 'rgba(78, 123, 255, 0.04)' }
          ])
        },
        itemStyle: {
          color: (params: any) => (distribution.value?.buckets[params.dataIndex]?.key === 'unknown' ? '#8f9ab1' : '#4e7bff')
        },
        markLine: markLineIndex >= 0
          ? {
              silent: true,
              symbol: 'none',
              label: {
                formatter: knownWordsCoverageRatio.value === null
                  ? `已掌握 COCA ${distribution.value.known_words_value}`
                  : `已掌握 COCA ${distribution.value.known_words_value} ${(knownWordsCoverageRatio.value * 100).toFixed(2)}%`,
                color: '#ef5a2d',
                fontWeight: 700
              },
              lineStyle: {
                color: '#ef5a2d',
                type: 'dashed',
                width: 2
              },
              data: [
                {
                  xAxis: labels[markLineIndex]
                }
              ]
            }
          : undefined
      }
    ]
  })
}

const loadDistribution = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    distribution.value = await request<DistributionResponse>(`/analysis/results/${props.resultId}/distribution`)
  } catch (error: any) {
    errorMessage.value = error?.data?.message || error?.message || '请稍后重试'
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
    await nextTick()
    renderChart()
  }
}

const resizeChart = () => {
  chart.value?.resize()
}

watch(
  () => props.resultId,
  async () => {
    distribution.value = null
    await loadDistribution()
  },
  { immediate: true }
)

onMounted(() => {
  window.addEventListener('resize', resizeChart)
})

watch(
  [distribution, loading],
  async ([nextDistribution, nextLoading]) => {
    if (!nextDistribution || nextLoading) {
      return
    }

    await nextTick()
    renderChart()
  },
  { flush: 'post' }
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart.value?.dispose()
  chart.value = null
})
</script>

<style scoped>
.distribution-card,
.distribution-head,
.distribution-state {
  display: grid;
  gap: 18px;
}

.distribution-note,
.distribution-footnote {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.8;
}

.distribution-chart {
  width: 100%;
  height: 340px;
}

.distribution-state {
  padding-block: 8px;
}

.distribution-error strong {
  font-size: 20px;
  line-height: 1.1;
}

.distribution-error p {
  margin: 0;
  color: var(--text-soft);
}

@media (max-width: 768px) {
  .distribution-chart {
    height: 320px;
  }
}
</style>
