<template>
  <div class="crud-container">
    <div class="crud-toolbar">
      <el-button type="primary" @click="openCreate">新增类别</el-button>
    </div>

    <el-table :data="list" v-loading="loading" border style="width: 100%">
      <el-table-column label="类别编码" width="120">
        <template #default="scope">{{ String(scope.row.category_code).padStart(3, '0') }}</template>
      </el-table-column>
      <el-table-column prop="category_name" label="类别名称" min-width="180" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="openEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑类别' : '新增类别'" width="420px">
      <el-form :model="form" label-width="80px">
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
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCategories, createCategory, updateCategory, deleteCategory } from '@/api/category'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = ref({ id: null, category_name: '' })

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

function openCreate() {
  isEdit.value = false
  form.value = { id: null, category_name: '' }
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  form.value = { id: row.id, category_name: row.category_name }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.category_name || !form.value.category_name.trim()) {
    ElMessage.warning('请输入类别名称')
    return
  }
  try {
    if (isEdit.value) {
      await updateCategory(form.value.id, { category_name: form.value.category_name.trim() })
      ElMessage.success('更新成功')
    } else {
      await createCategory({ category_name: form.value.category_name.trim() })
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
    await ElMessageBox.confirm(`确定删除类别「${row.category_name}」吗？`, '提示', { type: 'warning' })
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
}
</style>
