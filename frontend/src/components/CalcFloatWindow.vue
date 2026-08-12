<template>
  <teleport to="body">
    <div
      v-if="visible"
      ref="floatRef"
      class="calc-float"
      :style="posStyle"
      @mousedown.stop
    >
      <div class="calc-float-header" @mousedown="startDrag">
        <span class="calc-float-title">{{ title }}</span>
        <el-icon class="calc-float-close" @click="close"><Close /></el-icon>
      </div>
      <div class="calc-float-body">
        <slot />
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { Close } from '@element-plus/icons-vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '' }
})
const emit = defineEmits(['update:visible'])

// 位置：初始贴屏幕右下角（right/bottom），拖动后切换为 left/top 定位
const pos = ref({ right: 24, bottom: 24, left: null, top: null })
const dragging = ref(false)
const offset = ref({ x: 0, y: 0 })
const floatRef = ref(null)

const posStyle = computed(() => {
  const p = pos.value
  if (p.left !== null && p.top !== null) {
    return { left: `${p.left}px`, top: `${p.top}px` }
  }
  return { right: `${p.right}px`, bottom: `${p.bottom}px` }
})

function startDrag(e) {
  const el = floatRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  offset.value = { x: e.clientX - rect.left, y: e.clientY - rect.top }
  dragging.value = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  e.preventDefault()
}

function onDrag(e) {
  if (!dragging.value) return
  const left = e.clientX - offset.value.x
  const top = e.clientY - offset.value.y
  // 限制窗口不跑出可视区域（至少保留标题栏可见）
  const maxLeft = window.innerWidth - 120
  const maxTop = window.innerHeight - 40
  pos.value = {
    right: null,
    bottom: null,
    left: Math.max(0, Math.min(left, maxLeft)),
    top: Math.max(0, Math.min(top, maxTop))
  }
}

function stopDrag() {
  dragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}

function close() {
  // 只能手动点击关闭按钮才关闭
  emit('update:visible', false)
}

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
})
</script>

<style scoped>
.calc-float {
  position: fixed;
  width: 340px;
  background: #1f1f1f;
  border: 1px solid #333333;
  border-radius: 10px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
  overflow: hidden;
  user-select: none;
  /* 最上图层：高于抽屉(2000)与其他弹层 */
  z-index: 4000;
}

.calc-float-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 38px;
  padding: 0 12px;
  background: #2a2a2a;
  border-bottom: 1px solid #333333;
  cursor: move;
}

.calc-float-title {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 0.5px;
}

.calc-float-close {
  font-size: 16px;
  color: #a3a3a3;
  cursor: pointer;
  padding: 3px;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.calc-float-close:hover {
  color: #4ade80;
  background: rgba(255, 255, 255, 0.08);
}

.calc-float-body {
  padding: 14px;
}
</style>
