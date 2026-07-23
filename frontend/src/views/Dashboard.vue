<template>
  <transition name="fade" mode="out-in">
    <component :is="currentDashboard" />
  </transition>
</template>

<script setup>import { ref, watch } from 'vue';
import { useUserStore } from '@/store/user';
const userStore = useUserStore();
const currentDashboard = ref(null);
const loadDashboard = async (role) => {
 const dashboards = {
 boss: () => import('@/views/BossDashboard.vue'),
 sales: () => import('@/views/SalesDashboard.vue'),
 factory: () => import('@/views/FactoryDashboard.vue'),
 shipping: () => import('@/views/ShippingDashboard.vue')
 };
 const loader = dashboards[role] || dashboards['boss'];
 const module = await loader();
 currentDashboard.value = module.default;
};
loadDashboard(userStore.role || 'boss');
watch(() => userStore.role, (newRole) => {
 loadDashboard(newRole || 'boss');
});
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>