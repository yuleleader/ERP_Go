import exchangeRequest from '@/utils/exchangeRequest'

/**
 * 获取汇率数据
 * 使用免费的汇率API
 */
export function getExchangeRate() {
  return exchangeRequest.get('https://api.exchangerate-api.com/v4/latest/CNY')
}

/**
 * 获取指定货币对的汇率
 * @param {string} fromCurrency - 源货币
 */
export function getSpecificRate(fromCurrency) {
  return exchangeRequest.get(`https://api.exchangerate-api.com/v4/latest/${fromCurrency}`)
}

