<script lang="ts">
export interface BarSnapshot {
  x: number
  y: number
  width: number
  height: number
  color: string | CanvasPattern
  // For defense: second bar overlay
  overlayHeight?: number
  overlayColor?: string
}
</script>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  direction: 'in' | 'out'
  anchorIndex: number
  barPositions: BarSnapshot[]
  canvasWidth: number
  canvasHeight: number
  duration?: number
}>(), {
  duration: 400,
})

const emit = defineEmits<{
  (e: 'complete'): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let animationFrameId: number | null = null
let startTime: number | null = null

/**
 * Easing function: easeInOutCubic
 */
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

/**
 * Draw all bars at their interpolated positions for the current frame.
 */
function drawFrame(ctx: CanvasRenderingContext2D, progress: number): void {
  const easedProgress = easeInOutCubic(progress)

  ctx.clearRect(0, 0, props.canvasWidth, props.canvasHeight)

  const anchor = props.barPositions[props.anchorIndex]
  if (!anchor) return

  // Target x for anchor bar is 0 (left edge)
  const targetX = 0

  for (let i = 0; i < props.barPositions.length; i++) {
    const bar = props.barPositions[i]

    if (i === props.anchorIndex) {
      // Anchor bar: interpolate x position
      let currentX: number
      if (props.direction === 'in') {
        // Slide from original x to left edge (0)
        currentX = bar.x + (targetX - bar.x) * easedProgress
      } else {
        // Slide from left edge (0) back to original x
        currentX = targetX + (bar.x - targetX) * easedProgress
      }

      // Draw main bar
      ctx.globalAlpha = 1
      ctx.fillStyle = bar.color
      ctx.fillRect(currentX, bar.y, bar.width, bar.height)

      // Draw defense overlay if present
      if (bar.overlayHeight != null && bar.overlayColor) {
        ctx.fillStyle = bar.overlayColor
        const overlayY = bar.y + bar.height - bar.overlayHeight
        ctx.fillRect(currentX, overlayY, bar.width, bar.overlayHeight)
      }
    } else {
      // Non-anchor bars: interpolate opacity
      let alpha: number
      if (props.direction === 'in') {
        // Fade out: opacity goes from 1 to 0
        alpha = 1 - easedProgress
      } else {
        // Fade in: opacity goes from 0 to 1
        alpha = easedProgress
      }

      // Draw main bar
      ctx.globalAlpha = alpha
      ctx.fillStyle = bar.color
      ctx.fillRect(bar.x, bar.y, bar.width, bar.height)

      // Draw defense overlay if present
      if (bar.overlayHeight != null && bar.overlayColor) {
        ctx.fillStyle = bar.overlayColor
        const overlayY = bar.y + bar.height - bar.overlayHeight
        ctx.fillRect(bar.x, overlayY, bar.width, bar.overlayHeight)
      }
    }
  }

  // Reset globalAlpha
  ctx.globalAlpha = 1
}

/**
 * Animation loop using requestAnimationFrame.
 */
function animate(timestamp: number): void {
  if (startTime === null) {
    startTime = timestamp
  }

  const elapsed = timestamp - startTime
  const progress = Math.min(elapsed / props.duration, 1.0)

  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  drawFrame(ctx, progress)

  if (progress >= 1.0) {
    // Animation complete
    animationFrameId = null
    emit('complete')
  } else {
    animationFrameId = requestAnimationFrame(animate)
  }
}

onMounted(() => {
  // Start animation on mount
  animationFrameId = requestAnimationFrame(animate)
})

onUnmounted(() => {
  // Clean up animation frame on unmount (handles interruption)
  if (animationFrameId !== null) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
})
</script>

<template>
  <canvas
    ref="canvasRef"
    :width="canvasWidth"
    :height="canvasHeight"
    class="absolute top-0 left-0 pointer-events-none"
  />
</template>
