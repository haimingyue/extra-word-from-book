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
  { key: 'exam_level:六级', mode: 'exam_level', value: '六级', label: '六级' },
  { key: 'exam_level:GRE', mode: 'exam_level', value: 'GRE', label: 'GRE' },
  { key: 'exam_level:TOEFL', mode: 'exam_level', value: 'TOEFL', label: '托福' }
]

const cocaRankOptions: KnownWordsOption[] = Array.from({ length: 15 }, (_, index) => {
  const value = String((index + 1) * 1000)
  return {
    key: `coca_rank:${value}`,
    mode: 'coca_rank' as const,
    value,
    label: `COCA ${value}`
  }
})

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
