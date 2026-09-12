import { ref, computed } from 'vue'

export interface TimezonePreset {
  value: string
  label: string
  region: string
}

export const TIMEZONE_PRESETS: TimezonePreset[] = [
  { value: 'Asia/Kolkata', label: 'India Standard Time (IST • UTC+05:30)', region: 'Asia & South Asia' },
  { value: 'UTC', label: 'Coordinated Universal Time (UTC • UTC+00:00)', region: 'Universal' },
  { value: 'Asia/Dubai', label: 'Gulf Standard Time (GST • UTC+04:00)', region: 'Middle East' },
  { value: 'Asia/Singapore', label: 'Singapore Standard Time (SGT • UTC+08:00)', region: 'Asia Pacific' },
  { value: 'Asia/Tokyo', label: 'Japan Standard Time (JST • UTC+09:00)', region: 'Asia Pacific' },
  { value: 'Europe/London', label: 'London / UK (GMT/BST • UTC+00:00/+01:00)', region: 'Europe' },
  { value: 'Europe/Paris', label: 'Paris / Western Europe (CET • UTC+01:00/+02:00)', region: 'Europe' },
  { value: 'Europe/Berlin', label: 'Berlin / Central Europe (CET • UTC+01:00/+02:00)', region: 'Europe' },
  { value: 'America/New_York', label: 'US Eastern Time (ET • UTC-05:00/-04:00)', region: 'Americas' },
  { value: 'America/Chicago', label: 'US Central Time (CT • UTC-06:00/-05:00)', region: 'Americas' },
  { value: 'America/Denver', label: 'US Mountain Time (MT • UTC-07:00/-06:00)', region: 'Americas' },
  { value: 'America/Los_Angeles', label: 'US Pacific Time (PT • UTC-08:00/-07:00)', region: 'Americas' },
  { value: 'Australia/Sydney', label: 'Sydney / Eastern Australia (AEST • UTC+10:00/+11:00)', region: 'Oceania' }
]

export const DEFAULT_TIMEZONE = 'Asia/Kolkata'

// Global reactive singleton state
const selectedTimezone = ref<string>(DEFAULT_TIMEZONE)
const is24Hour = ref<boolean>(false)
let initialized = false

/**
 * Validates whether a given timezone string is recognized by the JavaScript runtime.
 */
export function isValidTimezone(tz: string): boolean {
  if (!tz || typeof tz !== 'string') return false
  try {
    Intl.DateTimeFormat(undefined, { timeZone: tz })
    return true
  } catch (e) {
    return false
  }
}

/**
 * Safe UTC Date Parser.
 * Normalizes timestamps arriving from Cloud (PostgreSQL ISO strings)
 * or Local (SQLite timestamps like '2026-09-12 13:10:31' or numeric ms).
 * If no timezone offset exists, appends 'Z' so browsers parse it as UTC rather than device local time.
 */
export function parseToUtcDate(ts: string | number | Date | null | undefined): Date | null {
  if (!ts) return null
  if (ts instanceof Date) return isNaN(ts.getTime()) ? null : ts
  if (typeof ts === 'number') {
    const d = new Date(ts)
    return isNaN(d.getTime()) ? null : d
  }
  if (typeof ts === 'string') {
    let s = ts.trim()
    if (!s) return null
    // Replace SQLite space separator with 'T'
    if (s.includes(' ') && !s.includes('T')) {
      s = s.replace(' ', 'T')
    }
    // If no timezone offset (+/-HH:MM) and no trailing Z, treat as UTC
    if (!s.endsWith('Z') && !s.slice(10).includes('+') && !s.slice(10).includes('-')) {
      s = s + 'Z'
    }
    const d = new Date(s)
    return isNaN(d.getTime()) ? null : d
  }
  return null
}

export const useAppTimezone = () => {
  // Initialize from localStorage and fetch server settings on client
  if (import.meta.client && !initialized) {
    initialized = true
    try {
      const savedTz = localStorage.getItem('washqueue_timezone')
      if (savedTz && isValidTimezone(savedTz)) {
        selectedTimezone.value = savedTz
      }

      const saved24 = localStorage.getItem('washqueue_time_24h')
      if (saved24 !== null) {
        is24Hour.value = saved24 === 'true'
      }

      // Sync across browser tabs/windows
      window.addEventListener('storage', (e) => {
        if (e.key === 'washqueue_timezone' && e.newValue && isValidTimezone(e.newValue)) {
          selectedTimezone.value = e.newValue
        }
        if (e.key === 'washqueue_time_24h' && e.newValue !== null) {
          is24Hour.value = e.newValue === 'true'
        }
      })

      // Custom in-app event for instant intra-window reactivity
      window.addEventListener('washqueue_timezone_change', ((e: CustomEvent) => {
        if (e.detail?.timezone && isValidTimezone(e.detail.timezone)) {
          selectedTimezone.value = e.detail.timezone
        }
        if (e.detail?.is24Hour !== undefined) {
          is24Hour.value = !!e.detail.is24Hour
        }
      }) as EventListener)

      // If no local preference was saved, query server settings endpoint
      if (!savedTz) {
        fetch('/api/system/settings')
          .then(res => res.json())
          .then(data => {
            if (data?.timezone && isValidTimezone(data.timezone)) {
              selectedTimezone.value = data.timezone
            }
          })
          .catch(() => {
            // Keep default Asia/Kolkata
          })
      }
    } catch (e) {
      // Storage unavailable, fallback to default
    }
  }

  /**
   * Update active timezone and persist to localStorage + broadcast to other tabs.
   */
  const setTimezone = (tz: string) => {
    if (!isValidTimezone(tz)) {
      throw new Error(`Invalid timezone identifier: ${tz}`)
    }
    selectedTimezone.value = tz
    if (import.meta.client) {
      try {
        localStorage.setItem('washqueue_timezone', tz)
        window.dispatchEvent(new CustomEvent('washqueue_timezone_change', { detail: { timezone: tz } }))
      } catch (e) {}
    }
  }

  /**
   * Toggle or set 24-hour time format.
   */
  const setTimeFormat = (is24: boolean) => {
    is24Hour.value = is24
    if (import.meta.client) {
      try {
        localStorage.setItem('washqueue_time_24h', String(is24))
        window.dispatchEvent(new CustomEvent('washqueue_timezone_change', { detail: { is24Hour: is24 } }))
      } catch (e) {}
    }
  }

  /**
   * Reset timezone to IST (Asia/Kolkata) default.
   */
  const resetToDefault = () => {
    setTimezone(DEFAULT_TIMEZONE)
    setTimeFormat(false)
  }

  /**
   * Format a timestamp into clock time (e.g. "07:15 PM" or "19:15").
   */
  const formatTime = (ts: string | number | Date | null | undefined, options?: Intl.DateTimeFormatOptions): string => {
    const d = parseToUtcDate(ts)
    if (!d) return '—'
    try {
      return new Intl.DateTimeFormat('en-IN', {
        timeZone: selectedTimezone.value,
        hour: '2-digit',
        minute: '2-digit',
        hour12: !is24Hour.value,
        ...options
      }).format(d)
    } catch (e) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  }

  /**
   * Format a timestamp into clock time with seconds (e.g. "07:15:30 PM" or "19:15:30").
   */
  const formatTimeWithSeconds = (ts: string | number | Date | null | undefined): string => {
    const d = parseToUtcDate(ts)
    if (!d) return 'Never'
    try {
      return new Intl.DateTimeFormat('en-IN', {
        timeZone: selectedTimezone.value,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: !is24Hour.value
      }).format(d)
    } catch (e) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    }
  }

  /**
   * Format a date into full readable date (e.g. "Saturday, 12 September 2026").
   */
  const formatDate = (ts: string | number | Date | null | undefined = new Date()): string => {
    const d = parseToUtcDate(ts) || new Date()
    try {
      return new Intl.DateTimeFormat('en-IN', {
        timeZone: selectedTimezone.value,
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      }).format(d)
    } catch (e) {
      return d.toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
    }
  }

  /**
   * Format short date (e.g. "12 Sep 2026").
   */
  const formatDateShort = (ts: string | number | Date | null | undefined = new Date()): string => {
    const d = parseToUtcDate(ts) || new Date()
    try {
      return new Intl.DateTimeFormat('en-IN', {
        timeZone: selectedTimezone.value,
        day: 'numeric',
        month: 'short',
        year: 'numeric'
      }).format(d)
    } catch (e) {
      return d.toLocaleDateString()
    }
  }

  /**
   * Combined date and time (e.g. "12 Sep 2026, 07:15 PM").
   */
  const formatDateTime = (ts: string | number | Date | null | undefined): string => {
    const d = parseToUtcDate(ts)
    if (!d) return '—'
    try {
      return new Intl.DateTimeFormat('en-IN', {
        timeZone: selectedTimezone.value,
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: !is24Hour.value
      }).format(d)
    } catch (e) {
      return d.toLocaleString()
    }
  }

  /**
   * Returns short timezone code (e.g. "IST", "EST", "UTC").
   */
  const getTimezoneAbbr = (ts?: Date): string => {
    const d = ts || new Date()
    try {
      const parts = new Intl.DateTimeFormat('en-US', {
        timeZone: selectedTimezone.value,
        timeZoneName: 'short'
      }).formatToParts(d)
      const part = parts.find(p => p.type === 'timeZoneName')
      return part ? part.value : selectedTimezone.value
    } catch (e) {
      return selectedTimezone.value
    }
  }

  /**
   * Returns GMT/UTC offset string (e.g. "UTC+05:30", "UTC+00:00").
   */
  const getTimezoneOffsetStr = (ts?: Date): string => {
    const d = ts || new Date()
    try {
      const parts = new Intl.DateTimeFormat('en-US', {
        timeZone: selectedTimezone.value,
        timeZoneName: 'longOffset'
      }).formatToParts(d)
      const part = parts.find(p => p.type === 'timeZoneName')
      if (part) {
        return part.value.replace('GMT', 'UTC')
      }
      return 'UTC'
    } catch (e) {
      return 'UTC'
    }
  }

  /**
   * Active timezone label (human friendly from presets or fallback).
   */
  const activeTimezoneLabel = computed(() => {
    const match = TIMEZONE_PRESETS.find(p => p.value === selectedTimezone.value)
    if (match) return match.label
    return `${selectedTimezone.value} (${getTimezoneOffsetStr()})`
  })

  return {
    selectedTimezone,
    is24Hour,
    activeTimezoneLabel,
    availablePresets: TIMEZONE_PRESETS,
    defaultTimezone: DEFAULT_TIMEZONE,
    isValidTimezone,
    parseToUtcDate,
    formatTime,
    formatTimeWithSeconds,
    formatDate,
    formatDateShort,
    formatDateTime,
    getTimezoneAbbr,
    getTimezoneOffsetStr,
    setTimezone,
    setTimeFormat,
    resetToDefault
  }
}
