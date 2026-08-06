<template>
  <div class="crud-container">
    <div class="crud-toolbar">
      <el-button type="primary" @click="openCreate(null)">新增一级类别</el-button>
      <span class="toolbar-tip">一级编码为三位数字（如 002），其下二级编码自动拼接为六位（如 002001）</span>
    </div>

    <el-table
      :data="list"
      v-loading="loading"
      border
      row-key="id"
      default-expand-all
      :tree-props="{ children: 'children' }"
      style="width: 100%"
    >
      <el-table-column label="类别编码" width="140" prop="category_code" />
      <el-table-column prop="category_name" label="类别名称" min-width="200" />
      <el-table-column label="层级" width="100">
        <template #default="scope">
          <el-tag size="small" :type="scope.row.level === 1 ? '' : 'info'">
            {{ scope.row.level === 1 ? '一级' : '二级' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="scope">
          <el-button v-if="scope.row.level === 1" size="small" type="primary" link @click="openCreate(scope.row)">
            新增子类别
          </el-button>
          <el-button size="small" @click="openEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="440px">
      <el-form :model="form" label-width="90px">
        <el-form-item v-if="parentRow" label="上级类别">
          <el-input :model-value="`${parentRow.category_code} ${parentRow.category_name}`" disabled />
        </el-form-item>
        <el-form-item label="类别名称" required>
          <el-input v-model="form.category_name" placeholder="请输入类别名称" maxlength="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCategories, createCategory, updateCategory, deleteCategory } from '@/api/category'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const parentRow = ref(null)
const form = ref({ id: null, category_name: '' })

const dialogTitle = computed(() => {
  if (isEdit.value) return '编辑类别'
  return parentRow.value ? '新增子类别' : '新增一级类别'
})

async function fetchList() {
  loading.value = true
  try {
    list.value = await getCategories()
  } catch (e) {
    ElMessage.error('获取类别列表失败')
  } finally {
    loading.value = false
  }
}

function openCreate(parent) {
  isEdit.value = false
  parentRow.value = parent || null
  form.value = { id: null, category_name: '' }
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  parentRow.value = null
  form.value = { id: row.id, category_name: row.category_name }
  dialogVisible.value = true
}

async function submit() {
  const name = (form.value.category_name || '').trim()
  if (!name) {
    ElMessage.warning('请输入类别名称')
    return
  }
  try {
    if (isEdit.value) {
      await updateCategory(form.value.id, { category_name: name })
      ElMessage.success('更新成功')
    } else {
      await createCategory({ category_name: name, parent_id: parentRow.value?.id || null })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchList()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(row) {
  try {
    const tip = row.children?.length
      ? `类别「${row.category_name}」下存在 ${row.children.length} 个子类别，需先删除子类别`
      : `确定删除类别「${row.category_name}」吗？`
    if (row.children?.length) {
      ElMessage.warning(tip)
      return
    }
    await ElMessageBox.confirm(tip, '提示', { type: 'warning' })
    await deleteCategory(row.id)
    ElMessage.success('删除成功')
    await fetchList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(fetchList)
</script>

<style scoped>
.crud-container {
  padding: 16px;
}
.crud-toolbar {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.toolbar-tip {
  color: #909399;
  font-size: 12px;
}
</style>
