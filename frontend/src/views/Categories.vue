<template>
  <div class="categories-page">
    <div class="page-body">
      <!-- 左：所有类别（品牌式平铺列表，一级 + 二级缩进） -->
      <div class="left-panel">
        <div class="left-title">所有类别</div>
        <div class="left-list" v-loading="loading">
          <div
            class="left-item"
            :class="{ active: !selectedNode }"
            @click="onTreeSelect(null)"
          >
            全部
          </div>
          <template v-for="cat in categoryTree" :key="cat.id">
            <div
              class="left-item"
              :class="{ active: selectedNode && selectedNode.id === cat.id }"
              @click="onTreeSelect(cat)"
            >
              <span class="item-name">{{ cat.category_name }}</span>
              <span class="item-code">{{ cat.category_code }}</span>
            </div>
            <div
              v-for="child in cat.children || []"
              :key="child.id"
              class="left-item left-item-child"
              :class="{ active: selectedNode && selectedNode.id === child.id }"
              @click="onTreeSelect(child)"
            >
              <span class="item-name">{{ child.category_name }}</span>
              <span class="item-code">{{ child.category_code }}</span>
            </div>
          </template>
          <div v-if="!loading && (!categoryTree || categoryTree.length === 0)" class="left-empty">
            暂无类别
          </div>
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
              <el-tag v-if="row.isSelf" size="small" type="warning" style="margin-left: 6px;">本类</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 类别新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="420px"
      @closed="resetDialog"
    >
      <el-form>
        <el-form-item label="类别名称">
          <el-input v-model="dialogName" maxlength="100" show-word-limit placeholder="请输入类别名称" />
        </el-form-item>
        <el-form-item v-if="dialogMode === 'edit'" label="类别编码">
          <span class="readonly-code">{{ dialogTargetCode }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmDialog" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增商品对话框（简化版：只填名称） -->
    <el-dialog
      v-model="productDialogVisible"
      title="新增商品"
      width="420px"
      @closed="productDialogName = ''"
    >
      <el-form>
        <el-form-item label="所属类别">
          <span class="readonly-code">{{ selectedNode ? `[${selectedNode.category_code}]${selectedNode.category_name}` : '—' }}</span>
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
defineOptions({ name: 'Categories' })
/**
 * 类别管理（导航管理 > 类别）
 * - 左：所有类别列表（品牌式平铺，一级 + 二级缩进）
 * - 右：按左侧选中层级切换右表内容（根=一级 / 选一级=父类自身+其下二级 / 选二级=商品）
 * - 操作：新增/修改/删除
 * - 删除：有子项禁删
 * - 查询：输入关键字点击"查询"（或回车）过滤当前右表
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { checkDataPerm } from '@/utils/dataPerm'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCategories, createCategory, updateCategory, deleteCategory } from '@/api/category'
import { getProducts, createProduct } from '@/api/product'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const saving = ref(false)

const categoryTree = ref([])
const selectedNode = ref(null)

// ===== 类别列表加载 =====
async function fetchCategories() {
  loading.value = true
  try {
    categoryTree.value = (await getCategories()) || []
  } catch (e) {
    ElMessage.error('加载类别失败')
  } finally {
    loading.value = false
  }
}

// 在列表中按 id 查找节点（重新加载后用此恢复选中）
function findNodeById(nodes, id) {
  for (const n of nodes) {
    if (n.id === id) return n
    if (n.children?.length) {
      const f = findNodeById(n.children, id)
      if (f) return f
    }
  }
  return null
}

// ===== 选中 =====
function onTreeSelect(node) {
  selectedNode.value = node
  resetQuery()
}

// ===== 当前层级与右表内容 =====
const selectedLevel = computed(() => selectedNode.value?.level || 0)
// 0=根（未选），1=一级，2=二级

const allRows = ref([])  // 当前右表的"原始"数据（不经过筛选）

const currentTableTitle = computed(() => {
  if (selectedLevel.value === 0) return '全部一级类别'
  if (selectedLevel.value === 1) return `一级 [${selectedNode.value.category_code}]${selectedNode.value.category_name} 及其子类别`
  if (selectedLevel.value === 2) return `二级 [${selectedNode.value.category_code}]${selectedNode.value.category_name} 的商品`
  return ''
})

async function loadRightRows() {
  allRows.value = []
  if (selectedLevel.value === 0) {
    // 根：显示全部一级类别
    allRows.value = (categoryTree.value || []).map(n => ({
      id: n.id, code: n.category_code, name: n.category_name
    }))
    return
  }
  if (selectedLevel.value === 1) {
    // 选一级：父类自身 + 其下二级（父类排第一行，带"本类"标记）
    const children = selectedNode.value.children || []
    allRows.value = [
      {
        id: selectedNode.value.id,
        code: selectedNode.value.category_code,
        name: selectedNode.value.category_name,
        isSelf: true
      },
      ...children.map(n => ({
        id: n.id, code: n.category_code, name: n.category_name
      }))
    ]
    return
  }
  if (selectedLevel.value === 2) {
    // 选二级：加载其下商品
    loading.value = true
    try {
      const list = await getProducts({ category_id: selectedNode.value.id, limit: 500 })
      allRows.value = (list || []).map(p => ({
        id: p.id, code: p.product_code, name: p.product_name
      }))
    } catch (e) {
      ElMessage.error('加载商品失败')
    } finally {
      loading.value = false
    }
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

// 切换选中节点时清空查询条件
function resetQuery() {
  filterKeyword.value = ''
  appliedKeyword.value = ''
}

// ===== 按钮可用性 =====
const canAdd = computed(() => true)  // 任何层级都可新增
const canModify = computed(() => selectedLevel.value === 1 || selectedLevel.value === 2)
const canDelete = computed(() => canModify.value)

// ===== 账号数据权限（按钮是否显示；boss 恒显示） =====
const permAdd = computed(() => checkDataPerm(userStore.userInfo, 'category', 'add'))
const permModify = computed(() => checkDataPerm(userStore.userInfo, 'category', 'edit'))
const permDelete = computed(() => checkDataPerm(userStore.userInfo, 'category', 'delete'))

// ===== 类别新增/编辑 =====
const dialogVisible = ref(false)
const dialogMode = ref('add')      // add | edit
const dialogTargetId = ref(null)
const dialogTargetCode = ref('')
const dialogName = ref('')

const dialogTitle = computed(() => {
  if (dialogMode.value === 'add') {
    return selectedLevel.value === 0 ? '新增一级类别' : '新增子类别'
  }
  return '修改类别名称'
})

function showAddDialog() {
  if (selectedLevel.value === 2) {
    // 在二级下"新增"是新增商品
    showAddProductDialog()
    return
  }
  dialogMode.value = 'add'
  dialogTargetId.value = null
  dialogTargetCode.value = ''
  dialogName.value = ''
  dialogVisible.value = true
}

function showModifyDialog() {
  if (!selectedNode.value) return
  dialogMode.value = 'edit'
  dialogTargetId.value = selectedNode.value.id
  dialogTargetCode.value = selectedNode.value.category_code
  dialogName.value = selectedNode.value.category_name
  dialogVisible.value = true
}

function resetDialog() {
  dialogMode.value = 'add'
  dialogTargetId.value = null
  dialogTargetCode.value = ''
  dialogName.value = ''
}

async function confirmDialog() {
  const name = dialogName.value.trim()
  if (!name) {
    ElMessage.warning('请输入类别名称')
    return
  }
  saving.value = true
  try {
    if (dialogMode.value === 'add') {
      const payload = { category_name: name }
      // 一级：parent_id 不传；二级：parent_id = 当前一级节点 id
      if (selectedLevel.value === 1 && selectedNode.value) {
        payload.parent_id = selectedNode.value.id
      }
      await createCategory(payload)
      ElMessage.success('类别创建成功')
    } else {
      await updateCategory(dialogTargetId.value, { category_name: name })
      ElMessage.success('类别修改成功')
    }
    dialogVisible.value = false
    await refreshAll()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

// ===== 新增商品 =====
const productDialogVisible = ref(false)
const productDialogName = ref('')

function showAddProductDialog() {
  if (selectedLevel.value !== 2) return
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
      category_id: selectedNode.value.id
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

// ===== 删除（含子项禁删） =====
async function confirmDelete() {
  if (!selectedNode.value) {
    ElMessage.warning('请先在左侧选择一个类别节点')
    return
  }
  // 有子项禁删
  if (selectedLevel.value === 1 && selectedNode.value.children?.length) {
    ElMessage.warning('该一级类别下还有子类别，无法删除。请先删除或移走子类别。')
    return
  }
  if (selectedLevel.value === 2) {
    // 检查其下是否有商品
    loading.value = true
    let hasProduct = false
    try {
      const list = await getProducts({ category_id: selectedNode.value.id, limit: 1 })
      hasProduct = !!(list && list.length)
    } catch (e) {
      ElMessage.error('检查商品关联失败')
      return
    } finally {
      loading.value = false
    }
    if (hasProduct) {
      ElMessage.warning('该二级类别下还有商品，无法删除。请先删除或移走商品。')
      return
    }
  }
  try {
    await ElMessageBox.confirm(
      `确定要删除类别 [${selectedNode.value.category_code}]${selectedNode.value.category_name} 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await deleteCategory(selectedNode.value.id)
    ElMessage.success('类别已删除')
    selectedNode.value = null
    await refreshAll()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

// ===== 通用刷新 =====
async function refreshAll() {
  const prevId = selectedNode.value?.id
  await fetchCategories()
  // 恢复选中
  if (prevId) {
    selectedNode.value = findNodeById(categoryTree.value, prevId)
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
  await fetchCategories()
  await loadRightRows()
})
</script>

<style scoped>
.categories-page {
  padding: 16px 20px;
}

.page-body {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

/* ===== 左侧类别列表（品牌式） ===== */
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

/* 二级类别缩进，保持层级感 */
.left-item-child {
  padding-left: 30px;
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