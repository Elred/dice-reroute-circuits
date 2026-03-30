<script setup lang="ts">
import { ref, watch } from 'vue'
import { marked } from 'marked'

const appVersion = __APP_VERSION__

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>()

const htmlCache = ref<string>('')
const error = ref<string | null>(null)

function close() {
  emit('update:modelValue', false)
}

function onOverlayClick(e: MouseEvent) {
  if (e.target === e.currentTarget) close()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      document.addEventListener('keydown', onKeydown)
      if (!htmlCache.value && !error.value) {
        fetch('/doc/about.md')
          .then((res) => {
            if (!res.ok) throw new Error(`Failed to load documentation (${res.status})`)
            return res.text()
          })
          .then(async (text) => {
            htmlCache.value = String(await marked.parse(text))
          })
          .catch((err: unknown) => {
            error.value = err instanceof Error ? err.message : 'Failed to load documentation.'
          })
      }
    } else {
      document.removeEventListener('keydown', onKeydown)
    }
  }
)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      @click="onOverlayClick"
    >
      <div
        class="relative w-full max-w-2xl mx-4 rounded-lg border border-[#d69e2e]/30 bg-[#1a1d2e] max-h-[80vh] overflow-y-auto shadow-xl"
        @click.stop
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-[#d69e2e]/20">
          <span class="text-[#d69e2e] font-semibold tracking-wide">About Dice Reroute Circuits <span class="text-[#8892a4] font-normal text-sm">v{{ appVersion }}</span></span>
          <button
            @click="close"
            class="text-[#8892a4] hover:text-white transition-colors text-xl leading-none"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <!-- Content -->
        <div class="px-6 py-5">
          <div v-if="error" class="text-[#e53e3e] text-sm">{{ error }}</div>
          <div v-else-if="!htmlCache" class="text-[#8892a4] text-sm">Loading…</div>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div v-else class="prose" v-html="htmlCache" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.prose {
  color: #c8d0e0;
  font-size: 0.9rem;
  line-height: 1.5;
}

.prose :deep(h1),
.prose :deep(h2),
.prose :deep(h3) {
  color: #d69e2e;
  font-weight: 600;
  margin-top: 1.25em;
  margin-bottom: 0.5em;
}

.prose :deep(h1) { font-size: 1.4rem; }
.prose :deep(h2) { font-size: 1.2rem; }
.prose :deep(h3) { font-size: 1rem; }

.prose :deep(p) {
  margin-bottom: 0.75em;
}

.prose :deep(code) {
  background: #0f1117;
  color: #d69e2e;
  padding: 0.1em 0.35em;
  border-radius: 3px;
  font-size: 0.85em;
}

.prose :deep(ul),
.prose :deep(ol) {
  padding-left: 1.5em;
  margin-bottom: 0.75em;
}

.prose :deep(ul) { list-style: disc; }
.prose :deep(ol) { list-style: decimal; }

.prose :deep(li) {
  margin-bottom: 0.25em;
}

.prose :deep(strong) { color: #e2e8f0; }
.prose :deep(em) { color: #a0aec0; }

.prose :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1em;
  font-size: 0.85rem;
}

.prose :deep(thead tr) {
  border-bottom: 2px solid #d69e2e40;
}

.prose :deep(th) {
  text-align: left;
  padding: 0.4em 0.75em;
  color: #d69e2e;
  font-weight: 600;
  white-space: nowrap;
}

.prose :deep(td) {
  padding: 0.4em 0.75em;
  border-bottom: 1px solid #ffffff10;
  vertical-align: top;
}

.prose :deep(tbody tr:last-child td) {
  border-bottom: none;
}

.prose :deep(tbody tr:hover td) {
  background: #ffffff06;
}
</style>
