import { watch } from 'vue'
import { useReportStore } from '../stores/reportStore'
import { encode, decode } from '../utils/reportCardEncoder'

// Module-level flag to prevent the watcher from firing during restoration
let isRestoring = false

/** Reset module state between tests. Do not call in production code. */
export function _resetForTesting(): void {
  isRestoring = false
}

export function useUrlSync() {
  const reportStore = useReportStore()

  /**
   * Start watching reportStore.groups and keep the URL in sync.
   * Call once from App.vue after restoreFromUrl() completes.
   */
  function startSync(): void {
    watch(
      () => reportStore.groups,
      async (groups) => {
        // Guard: skip if restoration is in progress
        if (isRestoring) return

        if (groups.length === 0) {
          // Clear all r params
          history.replaceState(null, '', window.location.pathname)
          return
        }

        // Encode each group as an r param
        const params = new URLSearchParams()
        for (const group of groups) {
          const encoded = await encode({ request: group.request, bomber: false })
          params.append('r', encoded)
        }

        const url = '?' + params.toString()
        history.replaceState(null, '', url)

        // Warn if URL is too long
        const fullUrl = window.location.origin + window.location.pathname + url
        if (fullUrl.length > 1500) {
          console.warn(`shareable-report-url: URL may be too long for some platforms (${fullUrl.length} chars)`)
        }
      },
      { deep: true },
    )
  }

  /**
   * Read r params from window.location.search, decode each,
   * call reportStore.runReport for valid ones, then clear r params.
   * After all reports are restored, re-encodes the groups into the URL
   * so the URL reflects the restored state (the watcher won't fire for
   * groups that were already populated before startSync was called).
   */
  async function restoreFromUrl(): Promise<void> {
    isRestoring = true

    try {
      const params = new URLSearchParams(window.location.search)
      const rParams = params.getAll('r')

      for (let i = 0; i < rParams.length; i++) {
        const result = await decode(rParams[i])
        if (result.ok) {
          await reportStore.runReport(result.value.request)
        } else {
          console.warn(`shareable-report-url: skipping invalid r param at index ${i}: ${result.error}`)
        }
      }
    } finally {
      isRestoring = false
    }

    // Re-encode restored groups back into the URL. We do this after clearing
    // isRestoring so the watcher (if already active) won't double-write, but
    // we write unconditionally here because the watcher may not have fired yet
    // (it only fires on changes, not on the initial populated state).
    const groups = reportStore.groups
    if (groups.length === 0) {
      // No r params were present or all failed — clear the URL
      const newParams = new URLSearchParams(window.location.search)
      newParams.delete('r')
      const newSearch = newParams.toString()
      history.replaceState(null, '', newSearch ? '?' + newSearch : window.location.pathname)
    } else {
      const urlParams = new URLSearchParams()
      for (const group of groups) {
        const encoded = await encode({ request: group.request, bomber: false })
        urlParams.append('r', encoded)
      }
      history.replaceState(null, '', '?' + urlParams.toString())
    }
  }

  return { restoreFromUrl, startSync }
}
