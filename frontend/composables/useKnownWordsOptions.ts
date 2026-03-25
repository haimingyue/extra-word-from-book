export type KnownWordsMode = 'exam_level' | 'coca_rank'

export type KnownWordsSelection = {
  mode: KnownWordsMode
  value: string
}

export type KnownWordsOption = KnownWordsSelection & {
  key: string
  label: string
}

type KnownWordsOptionGroup = {
  label: string
  options: KnownWordsOption[]
}

const examLevelOptions: KnownWordsOption[] = [
  { key: 'exam_level:初中', mode: 'exam_level', value: '初中', label: '初中' },
  { key: 'exam_level:高中', mode: 'exam_level', value: '高中', label: '高中' },
  { key: 'exam_level:四级', mode: 'exam_level', value: '四级', label: '四级' },
  { key: 'exam_level:六级', mode: 'exam_level', value: '六级', label: '六级' }
]

const cocaRankOptions: KnownWordsOption[] = [
  { key: 'coca_rank:1000', mode: 'coca_rank', value: '1000', label: 'COCA 1000' },
  { key: 'coca_rank:2000', mode: 'coca_rank', value: '2000', label: 'COCA 2000' },
  { key: 'coca_rank:3000', mode: 'coca_rank', value: '3000', label: 'COCA 3000' },
  { key: 'coca_rank:5000', mode: 'coca_rank', value: '5000', label: 'COCA 5000' },
  { key: 'coca_rank:8000', mode: 'coca_rank', value: '8000', label: 'COCA 8000' },
  { key: 'coca_rank:10000', mode: 'coca_rank', value: '10000', label: 'COCA 10000' },
  { key: 'coca_rank:12000', mode: 'coca_rank', value: '12000', label: 'COCA 12000' },
  { key: 'coca_rank:15000', mode: 'coca_rank', value: '15000', label: 'COCA 15000' }
]

const knownWordsOptionGroups: KnownWordsOptionGroup[] = [
  { label: '考试标签', options: examLevelOptions },
  { label: 'COCA 档位', options: cocaRankOptions }
]

const knownWordsOptions = knownWordsOptionGroups.flatMap((group) => group.options)

const DEFAULT_KNOWN_WORDS_SELECTION: KnownWordsSelection = {
  mode: 'coca_rank',
  value: '3000'
}

export const useKnownWordsOptions = () => {
  const getKnownWordsLabel = (mode: KnownWordsMode | null | undefined, value: string | null | undefined) => {
    if (!mode || !value) {
      return '--'
    }

    const matched = knownWordsOptions.find((option) => option.mode === mode && option.value === value)
    if (matched) {
      return matched.label
    }

    if (mode === 'coca_rank') {
      return `COCA ${value}`
    }

    return value
  }

  const getKnownWordsOptionKey = (selection: KnownWordsSelection) => `${selection.mode}:${selection.value}`

  const parseKnownWordsOptionKey = (rawKey: string | null | undefined): KnownWordsSelection => {
    if (!rawKey) {
      return DEFAULT_KNOWN_WORDS_SELECTION
    }

    const [mode, ...rest] = rawKey.split(':')
    const value = rest.join(':')
    if ((mode === 'exam_level' || mode === 'coca_rank') && value) {
      return {
        mode,
        value
      }
    }

    return DEFAULT_KNOWN_WORDS_SELECTION
  }

  return {
    knownWordsOptions,
    knownWordsOptionGroups,
    defaultKnownWordsSelection: DEFAULT_KNOWN_WORDS_SELECTION,
    getKnownWordsLabel,
    getKnownWordsOptionKey,
    parseKnownWordsOptionKey
  }
}
