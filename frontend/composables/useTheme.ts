export type ThemeMode = 'light' | 'dark'

export const useTheme = () => {
  const theme = useState<ThemeMode>('theme-mode', () => 'light')

  const applyTheme = (nextTheme: ThemeMode) => {
    theme.value = nextTheme
    if (process.client) {
      document.documentElement.dataset.theme = nextTheme
      localStorage.setItem('theme-mode', nextTheme)
    }
  }

  const initTheme = () => {
    if (!process.client) {
      return
    }
    const stored = localStorage.getItem('theme-mode')
    const nextTheme: ThemeMode = stored === 'dark' ? 'dark' : 'light'
    applyTheme(nextTheme)
  }

  const toggleTheme = () => {
    applyTheme(theme.value === 'light' ? 'dark' : 'light')
  }

  return {
    theme,
    initTheme,
    applyTheme,
    toggleTheme
  }
}
