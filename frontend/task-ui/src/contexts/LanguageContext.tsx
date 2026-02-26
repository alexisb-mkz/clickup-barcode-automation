import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

export type Lang = 'en' | 'zh'

const STORAGE_KEY = 'preferred_lang'

interface LanguageContextValue {
  lang: Lang
  toggleLang: () => void
  setLang: (lang: Lang) => void
  /** Set language from translate_flag auto-detection — does NOT write to localStorage. */
  setLangAuto: (lang: Lang) => void
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'zh' ? 'zh' : 'en'
  })

  // Explicit user toggle — persists to localStorage
  const setLang = useCallback((newLang: Lang) => {
    localStorage.setItem(STORAGE_KEY, newLang)
    setLangState(newLang)
  }, [])

  // Auto-detection from translate_flag — does NOT write to localStorage
  const setLangAuto = useCallback((newLang: Lang) => {
    setLangState(newLang)
  }, [])

  const toggleLang = useCallback(() => {
    setLang(lang === 'en' ? 'zh' : 'en')
  }, [lang, setLang])

  return (
    <LanguageContext.Provider value={{ lang, toggleLang, setLang, setLangAuto }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider')
  return ctx
}

/** Returns true if the user has explicitly toggled the language before. */
export function hasStoredLangPreference(): boolean {
  return localStorage.getItem(STORAGE_KEY) !== null
}
