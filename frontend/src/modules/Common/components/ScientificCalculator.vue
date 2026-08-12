<template>
  <div class="sci-wrapper">
    <div class="sci-display">
      <div class="sci-expr" v-if="expression">{{ expression }}</div>
      <div class="sci-value" :class="{ error: display === '错误' }">{{ display }}</div>
    </div>

    <div class="sci-keys">
      <button class="key func" @click="clearAll">C</button>
      <button class="key func" @click="backspace">←</button>
      <button class="key func" @click="percent">%</button>
      <button class="key func" @click="negate">±</button>

      <button class="key num" @click="inputDigit('7')">7</button>
      <button class="key num" @click="inputDigit('8')">8</button>
      <button class="key num" @click="inputDigit('9')">9</button>
      <button class="key op" :class="{ active: operator === '÷' && waiting }" @click="setOperator('÷')">÷</button>

      <button class="key num" @click="inputDigit('4')">4</button>
      <button class="key num" @click="inputDigit('5')">5</button>
      <button class="key num" @click="inputDigit('6')">6</button>
      <button class="key op" :class="{ active: operator === '×' && waiting }" @click="setOperator('×')">×</button>

      <button class="key num" @click="inputDigit('1')">1</button>
      <button class="key num" @click="inputDigit('2')">2</button>
      <button class="key num" @click="inputDigit('3')">3</button>
      <button class="key op" :class="{ active: operator === '-' && waiting }" @click="setOperator('-')">−</button>

      <button class="key num zero" @click="inputDigit('0')">0</button>
      <button class="key num" @click="inputDot">.</button>
      <button class="key op equal" @click="equals">=</button>
      <button class="key op" :class="{ active: operator === '+' && waiting }" @click="setOperator('+')">+</button>
    </div>

    <div class="sci-hint">键盘：数字 0-9、. + − × ÷ % 、= 或 Enter 计算、Backspace 删除、Esc/C 清空、n 变号(±)</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// 显示内容
const display = ref('0')
// 上方表达式预览（如 12 + 3）
const expression = ref('')
// 上一个操作数
const previous = ref(null)
// 当前运算符
const operator = ref(null)
// 是否正在等待输入下一个操作数
const waiting = ref(false)

function format(n) {
  if (!isFinite(n)) return '错误'
  // 去除浮点误差，最多保留 10 位有效数字
  return String(parseFloat(n.toPrecision(12)))
}

function compute(a, b, op) {
  switch (op) {
    case '+': return a + b
    case '-': return a - b
    case '×': return a * b
    case '÷': return b === 0 ? NaN : a / b
    default: return b
  }
}

function inputDigit(d) {
  if (waiting.value) {
    display.value = d
    waiting.value = false
  } else {
    display.value = display.value === '0' || display.value === '错误'
      ? d
      : display.value + d
  }
}

function inputDot() {
  if (waiting.value) {
    display.value = '0.'
    waiting.value = false
    return
  }
  if (display.value === '错误') display.value = '0'
  if (!display.value.includes('.')) display.value += '.'
}

function setOperator(op) {
  const current = parseFloat(display.value)
  if (display.value === '错误') return

  if (operator.value !== null && !waiting.value) {
    const result = compute(previous.value, current, operator.value)
    display.value = format(result)
    previous.value = result
  } else {
    previous.value = current
  }

  operator.value = op
  expression.value = `${format(previous.value)} ${op}`
  waiting.value = true
}

function equals() {
  if (operator.value === null || waiting.value) {
    expression.value = ''
    return
  }
  const current = parseFloat(display.value)
  const result = compute(previous.value, current, operator.value)
  expression.value = `${format(previous.value)} ${operator.value} ${format(current)} =`
  display.value = format(result)
  previous.value = null
  operator.value = null
  waiting.value = true
}

function percent() {
  if (display.value === '错误') return
  const current = parseFloat(display.value)
  let val = current / 100
  // 若存在待计算的前值与运算符，则按“前值的百分之当前”计算（如 200 + 10% = 200 + 20）
  if (operator.value !== null && previous.value !== null) {
    val = previous.value * (current / 100)
  }
  display.value = format(val)
  waiting.value = true
}

function negate() {
  if (display.value === '0' || display.value === '错误') return
  display.value = display.value.startsWith('-')
    ? display.value.slice(1)
    : '-' + display.value
}

function clearAll() {
  display.value = '0'
  expression.value = ''
  previous.value = null
  operator.value = null
  waiting.value = false
}

function backspace() {
  if (waiting.value || display.value === '错误') return
  display.value = display.value.length > 1
    ? display.value.slice(0, -1)
    : '0'
}

// 键盘控制：组件挂载（即计算器在弹窗内显示）时生效，卸载时自动移除监听
function handleKeydown(e) {
  // 忽略带 Ctrl/Alt/Meta 的组合，避免与浏览器/系统快捷键冲突
  if (e.ctrlKey || e.metaKey || e.altKey) return

  const k = e.key
  if (k >= '0' && k <= '9') {
    inputDigit(k)
  } else if (k === '.') {
    inputDot()
  } else if (k === '+') {
    setOperator('+')
  } else if (k === '-') {
    setOperator('-')
  } else if (k === '*') {
    setOperator('×')
  } else if (k === '/') {
    e.preventDefault() // 防止触发浏览器“快速查找”
    setOperator('÷')
  } else if (k === '%') {
    percent()
  } else if (k === '=' || k === 'Enter') {
    e.preventDefault() // 避免再次激活被聚焦的按钮
    equals()
  } else if (k === 'Backspace') {
    e.preventDefault()
    backspace()
  } else if (k === 'Escape' || k === 'Delete' || k === 'c' || k === 'C') {
    clearAll()
  } else if (k === 'n' || k === 'N') {
    negate()
  }
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
</script>

<style scoped>
.sci-wrapper {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 显示屏 */
.sci-display {
  background: #1f1f1f;
  border: 1px solid #333333;
  border-radius: 8px;
  padding: 10px 12px;
  min-height: 56px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-end;
  overflow: hidden;
}

.sci-expr {
  font-size: 11px;
  color: #8c8c8c;
  min-height: 14px;
  letter-spacing: 0.3px;
}

.sci-value {
  font-size: 22px;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 0.5px;
  word-break: break-all;
  text-align: right;
}

.sci-value.error {
  color: #f87171;
  font-size: 18px;
}

/* 按键网格 */
.sci-keys {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.key {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #ffffff;
  border-radius: 8px;
  height: 38px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.key:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.2);
}

.key:active {
  transform: scale(0.94);
}

.key.num {
  background: rgba(255, 255, 255, 0.04);
}

.key.op {
  color: #4ade80;
  border-color: rgba(74, 222, 128, 0.3);
  background: rgba(74, 222, 128, 0.12);
}

.key.op:hover {
  background: rgba(74, 222, 128, 0.22);
  border-color: rgba(74, 222, 128, 0.5);
}

.key.op.active {
  background: rgba(74, 222, 128, 0.35);
  border-color: #4ade80;
  box-shadow: 0 0 0 1px rgba(74, 222, 128, 0.3);
}

.key.func {
  color: #e6f7ff;
  font-size: 13px;
}

.key.equal {
  color: #0a0a0a;
  background: #4ade80;
  border-color: #4ade80;
  font-weight: 700;
}

.key.equal:hover {
  background: #6ee7a0;
  border-color: #6ee7a0;
}

.key.zero {
  /* 占一格即可 */
}

/* 键盘提示 */
.sci-hint {
  font-size: 10px;
  line-height: 1.4;
  color: #6b6b6b;
  text-align: center;
  margin-top: 2px;
  letter-spacing: 0.2px;
  user-select: none;
}
</style>
