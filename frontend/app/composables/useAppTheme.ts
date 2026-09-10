import { ref, watch, onMounted } from 'vue'

// Shared singleton state so all components in the app stay synchronized
const isDark = ref(false) // Default to LIGHT mode
const isInitialized = ref(false)

const updateHtmlClass = (dark: boolean) => {
  if (typeof document !== 'undefined') {
    if (dark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }
}

export function useAppTheme() {
  const initTheme = () => {
    if (typeof window === 'undefined' || isInitialized.value) return
    isInitialized.value = true

    const saved = localStorage.getItem('washqueue_theme')
    if (saved) {
      isDark.value = saved === 'dark'
    } else {
      // Default to Light mode
      isDark.value = false
      localStorage.setItem('washqueue_theme', 'light')
    }
    updateHtmlClass(isDark.value)

    // Listen for changes from other tabs
    window.addEventListener('storage', (e) => {
      if (e.key === 'washqueue_theme' && e.newValue) {
        isDark.value = e.newValue === 'dark'
        updateHtmlClass(isDark.value)
      }
    })
  }

  const toggleTheme = () => {
    isDark.value = !isDark.value
    if (typeof window !== 'undefined') {
      localStorage.setItem('washqueue_theme', isDark.value ? 'dark' : 'light')
    }
    updateHtmlClass(isDark.value)
  }

  const setTheme = (theme: 'light' | 'dark') => {
    isDark.value = theme === 'dark'
    if (typeof window !== 'undefined') {
      localStorage.setItem('washqueue_theme', theme)
    }
    updateHtmlClass(isDark.value)
  }

  // Ensure HTML class is immediately synchronized
  watch(isDark, (val) => {
    updateHtmlClass(val)
  }, { immediate: true })

  onMounted(() => {
    initTheme()
  })

  return {
    isDark,
    toggleTheme,
    setTheme
  }
}
