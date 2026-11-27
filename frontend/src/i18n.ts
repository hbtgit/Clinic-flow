import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import am from './locales/am.json'
import en from './locales/en.json'

const saved = (() => {
  try {
    return localStorage.getItem('lang')
  } catch {
    return null
  }
})()

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, am: { translation: am } },
  lng: saved ?? 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export function setLanguage(lang: 'en' | 'am') {
  i18n.changeLanguage(lang)
  document.documentElement.lang = lang
  try {
    localStorage.setItem('lang', lang)
  } catch {
    /* storage unavailable */
  }
}

export default i18n
