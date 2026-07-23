<template>
  <div class="exchange-wrapper-inner">
    <div class="exchange-card" :class="{ expanded: isExpanded }">
      <div class="exchange-header" @click="isExpanded = !isExpanded">
        <span class="title">汇率计算器</span>
        <el-icon class="arrow-icon" :class="{ rotated: isExpanded }">
          <ArrowRight />
        </el-icon>
      </div>

      <div class="content-collapsed" v-show="!isExpanded">
        <div class="exchange-rates">
          <div class="rate-row">
            <span class="currency-text">{{ currencyMap[fromCurrency] }}</span>
            <el-icon class="swap-icon-mini clickable" @click.stop="swapCurrency"><Switch /></el-icon>
            <span class="currency-text">{{ currencyMap[toCurrency] }}</span>
          </div>
          <div class="rate-row">
            <span v-if="loading" class="rate-value loading">加载中...</span>
            <span v-else-if="error" class="rate-value error">获取失败</span>
            <span v-else class="rate-value">1 = {{ currentRate.toFixed(4) }}</span>
          </div>
        </div>
        <el-button
          type="primary"
          size="small"
          class="refresh-btn"
          :icon="Refresh"
          :loading="loading"
          @click.stop="fetchExchangeRate"
        >
          刷新
        </el-button>
      </div>

      <div class="content-expanded" v-show="isExpanded">
        <div class="currency-row">
          <el-select v-model="fromCurrency" placeholder="货币" @change="handleCurrencyChange" size="small">
            <el-option v-for="currency in currencies" :key="currency" :label="`${currencyMap[currency]}（${currency}）`" :value="currency" />
          </el-select>
          <el-icon class="swap-icon-mini clickable" @click="swapCurrency"><Switch /></el-icon>
          <el-select v-model="toCurrency" placeholder="货币" @change="handleCurrencyChange" size="small">
            <el-option v-for="currency in currencies" :key="currency" :label="`${currencyMap[currency]}（${currency}）`" :value="currency" />
          </el-select>
        </div>

        <div class="amount-row">
          <el-input
            v-model.number="fromAmount"
            type="number"
            placeholder="金额"
            :min="0"
            size="small"
            @input="calculateResult"
          />
          <el-icon class="swap-icon-mini"><Switch /></el-icon>
          <el-input
            v-model="toAmount"
            type="number"
            placeholder="结果"
            :disabled="true"
            size="small"
          />
        </div>

        <div class="rate-display" v-if="!loading">
          <div v-if="error" class="error-state">
            <span>{{ error }}</span>
          </div>
          <div v-else class="rate-info">
            <div class="rate-text">
              1 {{ currencyMap[fromCurrency] }} = {{ currentRate.toFixed(4) }} {{ currencyMap[toCurrency] }}
            </div>
          </div>
        </div>

        <div class="refresh-row">
          <el-button
            type="primary"
            size="small"
            :icon="Refresh"
            :loading="loading"
            @click="fetchExchangeRate"
          >
            刷新
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Coin,
  Refresh,
  Switch,
  Loading,
  Warning,
  ArrowRight,
  Close
} from '@element-plus/icons-vue'
import { getExchangeRate, getSpecificRate } from '@/api/exchange'

// 货币列表
const currencyMap = {
  'CNY': '人民币',
  'USD': '美元',
  'EUR': '欧元',
  'GBP': '英镑',
  'JPY': '日元',
  'HKD': '港币',
  'AUD': '澳元',
  'CAD': '加元'
}
const currencies = Object.keys(currencyMap)

// 状态管理
const isExpanded = ref(false)
const loading = ref(false)
const error = ref('')
const fromCurrency = ref('CNY')
const toCurrency = ref('USD')
const fromAmount = ref(1)
const toAmount = ref(0)
const rates = ref({})
const lastUpdateTime = ref(null)

// 当前汇率计算
const currentRate = computed(() => {
  // 如果币种相同，汇率为 1
  if (fromCurrency.value === toCurrency.value) {
    return 1
  }
  if (rates.value && rates.value[toCurrency.value]) {
    return rates.value[toCurrency.value]
  }
  return 0
})

// 美元汇率（用于收起状态显示）
const usdRate = computed(() => {
  if (rates.value && rates.value['USD']) {
    return rates.value['USD']
  }
  return 0.14 // 默认值
})

// 格式化时间（统一走 @/utils/format，按北京时间显示）

async function fetchExchangeRate() {
  loading.value = true
  error.value = ''
  try {
    const data = await getSpecificRate(fromCurrency.value)
    if (data && data.rates) {
      rates.value = data.rates
      lastUpdateTime.value = new Date()
      calculateResult()
      ElMessage.success('汇率更新成功')
    }
  } catch (err) {
    console.error('获取汇率失败:', err)
    error.value = '网络请求失败，请稍后重试'
    ElMessage.error('获取汇率失败，请检查网络连接')
  } finally {
    loading.value = false
  }
}

// 计算转换结果
function calculateResult() {
  if (fromAmount.value) {
    toAmount.value = (fromAmount.value * currentRate.value).toFixed(2)
  } else {
    toAmount.value = ''
  }
}

// 货币变更处理
function handleCurrencyChange() {
  if (fromCurrency.value !== toCurrency.value) {
    fetchExchangeRate()
  } else {
    // 币种相同时直接计算结果
    calculateResult()
  }
}

// 交换货币
function swapCurrency() {
  const temp = fromCurrency.value
  fromCurrency.value = toCurrency.value
  toCurrency.value = temp
  // 重新获取汇率
  handleCurrencyChange()
}

onMounted(() => {
  fetchExchangeRate()
})
</script>

<style scoped>
.exchange-wrapper-inner {
  width: 100%;
}

.exchange-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 8px 10px;
  color: #ffffff;
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.exchange-card.expanded {
  padding: 10px 12px;
}

/* 头部 */
.exchange-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  cursor: pointer;
}

.exchange-header .title {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: #ffffff;
}

.arrow-icon {
  color: #4ade80;
  font-size: 16px;
  transition: transform 0.3s;
  padding: 3px;
  border-radius: 5px;
}

.arrow-icon:hover {
  background: rgba(74, 222, 128, 0.1);
}

.arrow-icon.rotated {
  transform: rotate(90deg);
}

/* 收起状态内容 */
.content-collapsed,
.content-expanded {
  transition: opacity 0.3s;
}

.exchange-rates {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rate-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.currency-text {
  font-size: 11px;
  font-weight: 500;
  color: #e6f7ff;
}

.swap-icon-mini {
  color: #4ade80;
  font-size: 12px;
  flex-shrink: 0;
}

.swap-icon-mini.clickable {
  cursor: pointer;
  padding: 2px;
  border-radius: 3px;
  transition: all 0.2s;
}

.swap-icon-mini.clickable:hover {
  background: rgba(74, 222, 128, 0.15);
  transform: rotate(180deg);
}

.rate-value {
  font-size: 12px;
  font-weight: 600;
  color: #4ade80;
  letter-spacing: 0.1px;
}

.rate-value.loading {
  color: #8c8c8c;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.rate-value.error {
  color: #f87171;
}

/* 收起状态刷新按钮 */
.content-collapsed .refresh-btn {
  margin-top: 12px;
  width: 100%;
  --el-button-bg-color: rgba(74, 222, 128, 0.15);
  --el-button-hover-bg-color: rgba(74, 222, 128, 0.25);
  --el-button-text-color: #4ade80;
  --el-button-border-color: rgba(74, 222, 128, 0.3);
  border: 1px solid rgba(74, 222, 128, 0.3);
  border-radius: 8px;
  font-weight: 500;
}

.content-collapsed .refresh-btn:hover {
  --el-button-border-color: rgba(74, 222, 128, 0.5);
}

/* 展开状态样式 */
.currency-row,
.amount-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.currency-row :deep(.el-select),
.amount-row :deep(.el-input) {
  flex: 1;
}

.currency-row :deep(.el-select__wrapper),
.amount-row :deep(.el-input__wrapper) {
  background: #1f1f1f;
  border: 1px solid #333333;
  border-radius: 8px;
  box-shadow: none;
}

.currency-row :deep(.el-select__wrapper:hover),
.amount-row :deep(.el-input__wrapper:hover) {
  border-color: #4ade80;
}

.currency-row :deep(.el-select__wrapper.is-focused),
.amount-row :deep(.el-input__wrapper.is-focus) {
  border-color: #4ade80;
  box-shadow: 0 0 0 1px rgba(74, 222, 128, 0.2);
}

.currency-row :deep(.el-select__placeholder),
.currency-row :deep(.el-select__selected-item),
.amount-row :deep(.el-input__inner) {
  color: #ffffff;
}

.amount-row :deep(.el-input__inner::placeholder) {
  color: #737373;
}

/* 汇率显示 */
.rate-display {
  background: rgba(74, 222, 128, 0.1);
  border: 1px solid rgba(74, 222, 128, 0.3);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  text-align: center;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #a3a3a3;
}

.error-state {
  color: #f87171;
}

.rate-info .rate-text {
  font-size: 14px;
  font-weight: 600;
  color: #4ade80;
  letter-spacing: 0.3px;
}

.refresh-row {
  display: flex;
  justify-content: center;
}

.refresh-row :deep(.el-button) {
  width: 100%;
  --el-button-bg-color: rgba(74, 222, 128, 0.15);
  --el-button-hover-bg-color: rgba(74, 222, 128, 0.25);
  --el-button-text-color: #4ade80;
  --el-button-border-color: rgba(74, 222, 128, 0.3);
  border: 1px solid rgba(74, 222, 128, 0.3);
  border-radius: 8px;
  font-weight: 500;
}

.refresh-row :deep(.el-button:hover) {
  --el-button-border-color: rgba(74, 222, 128, 0.5);
}

/* 下拉菜单深色主题 */
:deep(.el-select-dropdown) {
  background: #1f1f1f;
  border: 1px solid #333333;
  border-radius: 8px;
}

:deep(.el-select-dropdown__item) {
  color: #ffffff;
}

:deep(.el-select-dropdown__item:hover) {
  background: #2d2d2d;
}

:deep(.el-select-dropdown__item.selected) {
  background: rgba(74, 222, 128, 0.2);
  color: #4ade80;
}

:deep(.el-popper__arrow) {
  display: none;
}

/* 响应式适配 - 移动端 */
@media (max-width: 768px) {
  .exchange-container {
    left: 10px;
    bottom: 10px;
    right: 10px;
  }
  
  .exchange-card {
    width: 100%;
    max-width: 280px;
  }
  
  .exchange-card.expanded {
    width: 100%;
    max-width: 340px;
  }
}

/* 响应式适配 - 平板端 */
@media (min-width: 769px) and (max-width: 1024px) {
  .exchange-container {
    left: 15px;
    bottom: 15px;
  }
  
  .exchange-card {
    width: 200px;
  }
  
  .exchange-card.expanded {
    width: 360px;
  }
}

/* 大屏幕适配 */
@media (min-width: 1920px) {
  .exchange-container {
    left: 30px;
    bottom: 30px;
  }
}
</style>
