const DEFAULT_KNOWN_WORDS_LEVEL = 3000

export const useUserPreferences = () => {
  const defaultKnownWordsLevel = useState<number>('default-known-words-level', () => DEFAULT_KNOWN_WORDS_LEVEL)

  const initUserPreferences = () => {
    if (!process.client) {
      return
    }

    const rawLevel = localStorage.getItem('default-known-words-level')
    const parsedLevel = Number(rawLevel)
    if (Number.isFinite(parsedLevel) && parsedLevel >= 1000 && parsedLevel <= 15000) {
      defaultKnownWordsLevel.value = parsedLevel
    }
  }

  const setDefaultKnownWordsLevel = (level: number) => {
    defaultKnownWordsLevel.value = level
    if (process.client) {
      localStorage.setItem('default-known-words-level', String(level))
    }
  }

  return {
    defaultKnownWordsLevel,
    initUserPreferences,
    setDefaultKnownWordsLevel
  }
}
