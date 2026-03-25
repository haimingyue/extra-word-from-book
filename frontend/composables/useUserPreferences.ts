import type { KnownWordsSelection } from './useKnownWordsOptions'

const DEFAULT_KNOWN_WORDS_SELECTION: KnownWordsSelection = {
  mode: 'coca_rank',
  value: '3000'
}

export const useUserPreferences = () => {
  const defaultKnownWordsSelection = useState<KnownWordsSelection>(
    'default-known-words-selection',
    () => DEFAULT_KNOWN_WORDS_SELECTION
  )

  const initUserPreferences = () => {
    if (!process.client) {
      return
    }

    const rawSelection = localStorage.getItem('default-known-words-selection')
    if (rawSelection) {
      try {
        const parsedSelection = JSON.parse(rawSelection) as KnownWordsSelection
        if (
          (parsedSelection.mode === 'exam_level' || parsedSelection.mode === 'coca_rank')
          && typeof parsedSelection.value === 'string'
          && parsedSelection.value
        ) {
          defaultKnownWordsSelection.value = parsedSelection
          return
        }
      } catch {
        // 兼容旧版本本地存储，解析失败时继续回退。
      }
    }

    const rawLevel = localStorage.getItem('default-known-words-level')
    const parsedLevel = Number(rawLevel)
    if (Number.isFinite(parsedLevel) && parsedLevel >= 1000 && parsedLevel <= 15000) {
      defaultKnownWordsSelection.value = {
        mode: 'coca_rank',
        value: String(parsedLevel)
      }
    }
  }

  const setDefaultKnownWordsSelection = (selection: KnownWordsSelection) => {
    defaultKnownWordsSelection.value = selection
    if (process.client) {
      localStorage.setItem('default-known-words-selection', JSON.stringify(selection))
    }
  }

  return {
    defaultKnownWordsSelection,
    initUserPreferences,
    setDefaultKnownWordsSelection
  }
}
