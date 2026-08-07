<template>
  <teleport to="body">
    <transition name="fade">
      <div
        v-if="visible"
        class="sub-menu-mask"
        :style="maskStyle"
        @click.self="close"
      />
    </transition>
    <transition name="slide">
      <div
        v-if="visible"
        class="sub-menu-panel"
        :style="panelStyle"
      >
        <div class="panel-header">
          <span class="panel-title">{{ title }}</span>
          <el-icon class="panel-close" @click="close"><Close /></el-icon>
        </div>
        <div class="panel-body">
          <div
            v-for="group in groups"
            :key="group.title"
            class="menu-group"
          >
            <div class="group-title">{{ group.title }}</div>
            <div class="group-items">
              <div
                v-for="item in group.items"
                :key="item.path"
                class="menu-item"
                :class="{ active: item.path === currentPath }"
                @click="go(item)"
              >
                <span class="item-label" :title="item.label">{{ item.label }}</span>
              </div>
            </div>
          </div>
          <el-empty v-if="isEmpty" description="暂无可用功能" :image-size="80" />
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Close } from '@element-plus/icons-vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '' },
  groups: {
    type: Array,
    default: () => []
  },
  sidebarWidth: { type: Number, default: 200 },
  width: { type: Number, default: 320 }
})
const emit = defineEmits(['update:visible'])

const route = useRoute()
const router = useRouter()

const currentPath = computed(() => route.path)

const isEmpty = computed(() => {
  return !props.groups || props.groups.every((g) => !g.items || g.items.length === 0)
})

const panelStyle = computed(() => ({
  left: `${props.sidebarWidth}px`,
  width: `${props.width}px`
}))

const maskStyle = computed(() => ({
  left: `${props.sidebarWidth}px`
}))

function close() {
  emit('update:visible', false)
}

function go(item) {
  close()
  if (item.path && item.path !== route.path) {
    router.push(item.path)
  }
}
</script>

<style scoped>
.sub-menu-mask {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.25);
  z-index: 1999;
}

.sub-menu-panel {
  position: fixed;
  top: 0;
  bottom: 0;
  background: #fff;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 20px rgba(0, 0, 0, 0.1);
}

.panel-header {
  height: 60px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.panel-title {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}

.panel-close {
  font-size: 18px;
  color: #909399;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
}

.panel-close:hover {
  color: #409eff;
  background: #f5f7fa;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px 24px;
}

.menu-group {
  margin-bottom: 24px;
}

.menu-group:last-child {
  margin-bottom: 0;
}

.group-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 10px;
  padding-left: 8px;
  border-left: 3px solid #409eff;
  line-height: 1.2;
}

.group-items {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  height: 40px;
  padding: 0 8px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.menu-item:hover {
  border-color: #409eff;
  background: #f5f7fa;
  color: #409eff;
}

.menu-item.active {
  border-color: #409eff;
  background: #ecf5ff;
  color: #409eff;
}

.item-label {
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(-100%);
  opacity: 0;
}
</style>
