<template>
  <UniversalOrderList />
</template>

<script setup>
defineOptions({ name: 'Orders' })
/**
 * 订单列表页面
 *
 * 本页面使用通用订单列表组件（UniversalOrderList）实现多角色动态权限控制
 * 组件自动识别当前登录用户的系统角色（老板端/销售端/发货端/工厂端）
 * 动态适配：数据权限、列表展示字段、操作按钮、编辑权限、专属上传功能
 *
 * 角色权限对照：
 * - 老板端：查看全部订单、编辑全部订单、无删除权限
 * - 销售端：仅查看本人创建订单、编辑本人订单、删除本人订单（需密码验证）
 * - 发货端：查看全部订单、仅可编辑发货状态和物流信息、可上传发货凭证图片
 * - 工厂端：查看全部订单、不可编辑订单基础信息、仅可上传/删除生产进度图片
 */

import UniversalOrderList from '../components/UniversalOrderList.vue'
</script>

<style scoped>
.orders-container {
  /* 样式已由 UniversalOrderList 组件内部处理 */
}
</style>
