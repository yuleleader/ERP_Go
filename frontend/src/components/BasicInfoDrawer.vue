<template>
  <el-drawer
    v-model="visible"
    :title="title"
    direction="rtl"
    size="80%"
    destroy-on-close
  >
    <component :is="currentComponent" v-if="currentComponent" />
  </el-drawer>
</template>

<script setup>
import { computed, shallowRef } from 'vue'
import Products from '@/views/Products.vue'
import Shops from '@/views/Shops.vue'
import Users from '@/views/Users.vue'
import Logistics from '@/views/Logistics.vue'
import Categories from '@/views/Categories.vue'
import Brands from '@/views/Brands.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  module: { type: String, default: '' }
})
const emit = defineEmits(['update:visible'])

const visible = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v)
})

const metaMap = {
  products: { title: '商品管理', comp: Products },
  shops: { title: '网店信息', comp: Shops },
  users: { title: '用户管理', comp: Users },
  logistics: { title: '物流管理', comp: Logistics },
  categories: { title: '类别管理', comp: Categories },
  brands: { title: '品牌管理', comp: Brands }
}

const title = computed(() => metaMap[props.module]?.title || '基础信息')
const currentComponent = computed(() => metaMap[props.module]?.comp || null)
</script>
