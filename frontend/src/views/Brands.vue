<template>
  <div class="brands-page">
    <!-- 顶部面包屑 + 关闭按钮 -->
    <div class="page-header">
      <div class="breadcrumb">
        <span class="bc-current">品牌</span>
      </div>
      <el-button class="close-btn" link @click="goBack" title="关闭">
        <el-icon><Close /></el-icon>
      </el-button>
    </div>

    <div class="page-body">
      <!-- 左：所有品牌 -->
      <div class="left-panel">
        <div class="left-title">所有品牌</div>
        <div class="left-list" v-loading="loading">
          <div
            class="left-item"
            :class="{ active: !selectedBrand }"
            @click="onSelect(null)"
          >
            全部
          </div>
          <div
            v-for="b in brands"
            :key="b.id"
            class="left-item"
            :class="{ active: selectedBrand && selectedBrand.id === b.id }"
            @click="onSelect(b)"
          >
            <span class="item-name">{{ b.brand_name }}</span>
            <span class="item-code">{{ String(b.brand_code).padStart(3, '0') }}</span>
          </div>
          <div v-if="!loading && brands.length === 0" class="left-empty">暂无品牌</div>
        </div>
      </div>

      <!-- 右：详情面板 -->
      <div class="right-panel">
        <!-- 操作按钮组（显示与否由账号数据权限控制） -->
        <div class="action-bar">
          <el-button v-if="permAdd" :disabled="!canAdd" type="primary" plain @click="showAddDialog">新增</el-button>
          <el-button v-if="permModify" :disabled="!canModify" @click="showModifyDialog">修改</el-button>
          <el-button v-if="permDelete" :disabled="!canDelete" type="danger" plain @click="confirmDelete">删除</el-button>
        </div>

        <!-- 搜索框 -->
        <div class="search-bar">
          <span class="search-label">关键字：</span>
          <el-input
            v-model="filterKeyword"
            placeholder="关键字可输入编码、名称进行查询"
            clearable
            style="width: 280px;"
            @keyup.enter="applyQuery"
          />
          <el-button type="primary" @click="applyQuery" style="margin-left: 10px;">查询</el-button>
          <span class="table-title">{{ currentTableTitle }}</span>
        </div>

        <!-- 表格 -->
        <el-table :data="filteredRows" v-loading="loading" border style="width: 100%;" empty-text="暂无数据">
          <el-table-column type="index" label="行号" width="70" align="center" />
          <el-table-column prop="code" label="编码" min-width="180" />
          <el-table-column prop="name" label="名称" min-width="220">
            <template #default="{ row }">
              <span>{{ row.name }}</span>
              <el-tag v-if="row.isSelf" size="small" type="warning" style="margin-left: 6px;">本项</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 品牌新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="420px"
      @closed="dialogName = ''"
    >
      <el-form>
        <el-form-item v-if="dialogMode === 'edit'" label="品牌编码">
          <span class="readonly-code">{{ dialogTargetCode }}</span>
        </el-form-item>
        <el-form-item label="品牌名称">
          <el-input v-model="dialogName" maxlength="100" show-word-limit placeholder="请输入品牌名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmDialog" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增商品对话框（选中品牌下，简化版只填名称） -->
    <el-dialog
      v-model="productDialogVisible"
      title="新增商品"
      width="420px"
      @closed="productDialogName = ''"
    >
      <el-form>
        <el-form-item label="所属品牌">
          <span class="readonly-code">{{ selectedBrand ? `[${String(selectedBrand.brand_code).padStart(3, '0')}]${selectedBrand.brand_name}` : '—' }}</span>
        </el-form-item>
        <el-form-item label="商品名称">
          <el-input v-model="productDialogName" maxlength="100" show-word-limit placeholder="请输入商品名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="productDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAddProduct" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 品牌管理（导航管理 > 品牌），布局与类别管理一致
 * - 顶部面包屑 + 关闭
 * - 左：所有品牌列表
 * - 右：按左选切换右表（未选=全部品牌 / 选中=该品牌下的商品）
 * - 操作：新增/修改/删除（删除前检查该品牌下是否有商品，有则禁删）
 * - 查询：输入关键字点击"查询"（或回车）过滤当前右表
 */
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { checkDataPerm } from '@/utils/dataPerm'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Close } from '@element-plus/icons-vue'
import { getBrands, createBrand, updateBrand, deleteBrand } from '@/api/brand'
import { getProducts, createProduct } from '@/api/product'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const saving = ref(false)

const brands = ref([])
const selectedBrand = ref(null)

async function fetchBrands() {
  loading.value = true
  try {
    brands.value = (await getBrands()) || []
  } catch (e) {
    ElMessage.error('加载品牌失败')
  } finally {
    loading.value = false
  }
}

function onSelect(brand) {
  selectedBrand.value = brand
  resetQuery()
}

// ===== 当前右表内容 =====
const allRows = ref([])

const currentTableTitle = computed(() => {
  if (!selectedBrand.value) return '全部品牌'
  return `品牌 [${String(selectedBrand.value.brand_code).padStart(3, '0')}]${selectedBrand.value.brand_name} 的商品`
})

async function loadRightRows() {
  allRows.value = []
  if (!selectedBrand.value) {
    // 未选：显示全部品牌（第一行为"本项"标记？不需要，全部品牌就是品牌本身）
    allRows.value = (brands.value || []).map(b => ({
      id: b.id, code: String(b.brand_code).padStart(3, '0'), name: b.brand_name
    }))
    return
  }
  // 选中：该品牌自身 + 其下商品（品牌自身带"本项"标记，类比类别页父类）
  loading.value = true
  try {
    const list = await getProducts({ brand_id: selectedBrand.value.id, limit: 500 })
    allRows.value = [
      {
        id: selectedBrand.value.id,
        code: String(selectedBrand.value.brand_code).padStart(3, '0'),
        name: selectedBrand.value.brand_name,
        isSelf: true
      },
      ...(list || []).map(p => ({
        id: p.id, code: p.product_code, name: p.product_name
      }))
    ]
  } catch (e) {
    ElMessage.error('加载商品失败')
  } finally {
    loading.value = false
  }
}

// 查询：输入关键字后点击"查询"（或回车）才对当前右表过滤
const filterKeyword = ref('')
const appliedKeyword = ref('')

function applyQuery() {
  appliedKeyword.value = filterKeyword.value.trim().toLowerCase()
}

const filteredRows = computed(() => {
  const kw = appliedKeyword.value
  if (!kw) return allRows.value
  return allRows.value.filter(r =>
    String(r.code || '').toLowerCase().includes(kw) ||
    String(r.name || '').toLowerCase().includes(kw)
  )
})

function resetQuery() {
  filterKeyword.value = ''
  appliedKeyword.value = ''
}

// ===== 按钮可用性 =====
const canAdd = computed(() => true)          // 任何状态都可新增（未选=品牌 / 选中=商品）
const canModify = computed(() => !!selectedBrand.value)
const canDelete = computed(() => canModify.value)

// ===== 账号数据权限（按钮是否显示；boss 恒显示） =====
const permAdd = computed(() => checkDataPerm(userStore.userInfo, 'brand', 'add'))
const permModify = computed(() => checkDataPerm(userStore.userInfo, 'brand', 'edit'))
const permDelete = computed(() => checkDataPerm(userStore.userInfo, 'brand', 'delete'))

// ===== 新增/修改 =====
const dialogVisible = ref(false)
const dialogMode = ref('add')
const dialogTargetCode = ref('')
const dialogName = ref('')

const dialogTitle = computed(() =>
  dialogMode.value === 'add' ? '新增品牌' : '修改品牌名称'
)

function showAddDialog() {
  if (selectedBrand.value) {
    showAddProductDialog()
    return
  }
  dialogMode.value = 'add'
  dialogTargetCode.value = ''
  dialogName.value = ''
  dialogVisible.value = true
}

function showModifyDialog() {
  if (!selectedBrand.value) return
  dialogMode.value = 'edit'
  dialogTargetCode.value = String(selectedBrand.value.brand_code).padStart(3, '0')
  dialogName.value = selectedBrand.value.brand_name
  dialogVisible.value = true
}

async function confirmDialog() {
  const name = dialogName.value.trim()
  if (!name) {
    ElMessage.warning('请输入品牌名称')
    return
  }
  saving.value = true
  try {
    if (dialogMode.value === 'add') {
      await createBrand({ brand_name: name })
      ElMessage.success('品牌创建成功')
    } else {
      await updateBrand(selectedBrand.value.id, { brand_name: name })
      ElMessage.success('品牌修改成功')
    }
    dialogVisible.value = false
    await refreshAll()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

// ===== 新增商品（选中品牌下） =====
const productDialogVisible = ref(false)
const productDialogName = ref('')

function showAddProductDialog() {
  productDialogName.value = ''
  productDialogVisible.value = true
}

async function confirmAddProduct() {
  const name = productDialogName.value.trim()
  if (!name) {
    ElMessage.warning('请输入商品名称')
    return
  }
  if (name.length < 2) {
    ElMessage.warning('商品名称长度应在 2-100 字符之间')
    return
  }
  saving.value = true
  try {
    await createProduct({
      product_name: name,
      brand_id: selectedBrand.value.id
    })
    ElMessage.success('商品创建成功')
    productDialogVisible.value = false
    await refreshAll()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建商品失败')
  } finally {
    saving.value = false
  }
}

// ===== 删除（有商品禁删） =====
async function confirmDelete() {
  if (!selectedBrand.value) {
    ElMessage.warning('请先在左侧选择一个品牌')
    return
  }
  // 检查该品牌下是否有商品
  loading.value = true
  let hasProduct = false
  try {
    const list = await getProducts({ brand_id: selectedBrand.value.id, limit: 1 })
    hasProduct = !!(list && list.length)
  } catch (e) {
    ElMessage.error('检查商品关联失败')
    return
  } finally {
    loading.value = false
  }
  if (hasProduct) {
    ElMessage.warning('该品牌下还有商品，无法删除。请先删除或移走商品。')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要删除品牌 [${String(selectedBrand.value.brand_code).padStart(3, '0')}]${selectedBrand.value.brand_name} 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await deleteBrand(selectedBrand.value.id)
    ElMessage.success('品牌已删除')
    selectedBrand.value = null
    await refreshAll()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

// ===== 面包屑与关闭 =====
function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/dashboard')
  }
}

// ===== 通用刷新 =====
async function refreshAll() {
  const prevId = selectedBrand.value?.id
  await fetchBrands()
  if (prevId) {
    selectedBrand.value = (brands.value || []).find(b => b.id === prevId) || null
  }
  await loadRightRows()
}

onMounted(async () => {
  if (!userStore.token) {
    router.push('/login')
    return
  }
  if (!userStore.userInfo) {
    try { await userStore.fetchUserInfo() } catch (e) { /* noop */ }
  }
  await fetchBrands()
  await loadRightRows()
})
</script>

<style scoped>
.brands-page {
  padding: 16px 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  padding: 10px 16px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 12px;
}

.breadcrumb {
  font-size: 13px;
  color: #606266;
}

.bc-link {
  color: #409EFF;
  cursor: pointer;
  margin-right: 4px;
}
.bc-link:hover {
  text-decoration: underline;
}

.bc-sep {
  margin: 0 6px;
  color: #c0c4cc;
}

.bc-plain {
  color: #606266;
}

.bc-current {
  color: #303133;
  font-weight: 600;
}

.close-btn {
  font-size: 16px;
  color: #909399;
}

.page-body {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

/* ===== 左侧品牌列表 ===== */
.left-panel {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px;
}

.left-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f2f5;
  margin-bottom: 8px;
}

.left-list {
  max-height: calc(100vh - 240px);
  overflow-y: auto;
}

.left-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 9px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #303133;
  transition: background-color 0.15s;
}

.left-item:hover {
  background-color: #f5f7fa;
}

.left-item.active {
  background-color: #ecf5ff;
  color: #409EFF;
  font-weight: 600;
}

.item-code {
  font-size: 11px;
  color: #a8abb2;
  flex-shrink: 0;
  margin-left: 8px;
}

.left-empty {
  padding: 20px;
  text-align: center;
  color: #a8abb2;
  font-size: 12px;
}

/* ===== 右侧面板 ===== */
.right-panel {
  flex: 1;
  min-width: 0;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 14px;
}

.action-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f2f5;
  margin-bottom: 12px;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 0 10px 0;
}

.search-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.table-title {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}

.readonly-code {
  color: #606266;
  font-size: 13px;
}
</style>
