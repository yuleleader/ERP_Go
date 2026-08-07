<template>
  <div class="users-container">
    <!-- 左侧角色筛选面板 -->
    <aside class="role-panel">
      <div class="role-panel-title">角色筛选</div>
      <div
        class="role-item"
        :class="{ active: activeRole === '' }"
        @click="selectRole('')"
      >
        <span class="role-name">全部</span>
        <span class="role-count">{{ allUsersCount }}</span>
      </div>
      <div
        v-for="r in roleOptions"
        :key="r.value"
        class="role-item"
        :class="{ active: activeRole === r.value }"
        @click="selectRole(r.value)"
      >
        <span class="role-name">{{ r.label }}</span>
        <span class="role-count">{{ roleCounts[r.value] || 0 }}</span>
      </div>
    </aside>

    <!-- 右侧用户列表 -->
    <div class="users-main">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>用户管理</span>
            <el-button type="primary" @click="showCreateDialog">新建用户</el-button>
          </div>
        </template>

        <!-- 查询栏 -->
        <div class="search-bar">
          <el-input
            v-model="searchKeyword"
            placeholder="输入用户名或真实姓名查询"
            clearable
            style="width: 260px;"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
          <span v-if="activeRole" class="role-filter-tip">
            当前筛选：{{ roleLabel(activeRole) }}
          </span>
        </div>

        <el-table :data="users" v-loading="loading" style="width: 100%">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="username" label="用户名" />
          <el-table-column prop="real_name" label="真实姓名" />
          <el-table-column prop="role" label="角色" width="100">
            <template #default="{ row }">
              <el-tag :type="getRoleType(row.role)">{{ getRoleText(row.role) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="commission_rate" label="提成比例" width="100">
            <template #default="{ row }">
              {{ row.commission_rate ? row.commission_rate + '%' : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'">
                {{ row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="editUser(row)">编辑</el-button>
              <el-button link type="warning" size="small" @click="resetUserPassword(row)">重置密码</el-button>
              <el-button link type="danger" size="small" @click="handleDeleteUser(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" @closed="resetForm">
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" placeholder="请输入用户名" :disabled="dialogMode === 'edit'" />
        </el-form-item>
        <el-form-item label="真实姓名" prop="real_name">
          <el-input v-model="userForm.real_name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="dialogMode === 'create'">
          <el-input v-model="userForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" placeholder="请选择角色">
            <el-option label="老板端" value="boss" />
            <el-option label="销售端" value="sales" />
            <el-option label="工厂端" value="factory" />
            <el-option label="发货端" value="shipping" />
          </el-select>
        </el-form-item>
        <el-form-item label="提成比例" prop="commission_rate" v-if="userForm.role === 'sales'">
          <el-input-number v-model="userForm.commission_rate" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="价格权限">
          <el-checkbox-group v-model="userForm.price_permissions">
            <el-checkbox value="cost_price">成本价</el-checkbox>
            <el-checkbox value="retail_price">零售价</el-checkbox>
            <el-checkbox value="min_price">最低售价</el-checkbox>
          </el-checkbox-group>
          <div class="price-perm-tip">
            未勾选的价格，该账号在商品档案中显示为「***」。老板端不受此限制。
          </div>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="userForm.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitUser" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useUsersStore } from '@/store/users'
import { resetPassword } from '@/api/auth'
import { ElMessage, ElMessageBox } from 'element-plus'

const usersStore = useUsersStore()
const users = computed(() => usersStore.users)
const loading = computed(() => usersStore.loading)

// ===== 角色筛选 =====
const roleOptions = [
  { value: 'boss', label: '老板端' },
  { value: 'sales', label: '销售端' },
  { value: 'factory', label: '工厂端' },
  { value: 'shipping', label: '发货端' }
]
const activeRole = ref('')
const searchKeyword = ref('')

// 各角色数量（基于当前全部用户计算；若已有筛选数据则基于该数据统计）
const roleCounts = computed(() => {
  const counts = { boss: 0, sales: 0, factory: 0, shipping: 0 }
  for (const u of users.value) {
    if (counts[u.role] !== undefined) counts[u.role] += 1
  }
  return counts
})
const allUsersCount = computed(() => users.value.length)

function roleLabel(value) {
  return roleOptions.find(r => r.value === value)?.label || value
}

function selectRole(value) {
  activeRole.value = value
  handleSearch()
}

function handleSearch() {
  const params = {}
  const kw = searchKeyword.value.trim()
  if (kw) params.keyword = kw
  if (activeRole.value) params.role = activeRole.value
  usersStore.fetchUsers(params)
}

function handleReset() {
  searchKeyword.value = ''
  activeRole.value = ''
  usersStore.fetchUsers()
}

const dialogVisible = ref(false)
const dialogMode = ref('create')
const submitting = ref(false)
const currentUserId = ref(null)

const userFormRef = ref(null)
const userForm = reactive({
  username: '',
  real_name: '',
  password: '',
  role: 'sales',
  commission_rate: 10,
  price_permissions: ['cost_price', 'retail_price', 'min_price'],
  is_active: true
})

const userRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

const dialogTitle = computed(() => dialogMode.value === 'create' ? '新建用户' : '编辑用户')

function getRoleType(role) {
  return { boss: 'danger', sales: 'primary', factory: 'warning', shipping: 'info' }[role] || ''
}

function getRoleText(role) {
  return { boss: '老板端', sales: '销售端', factory: '工厂端', shipping: '发货端' }[role] || role
}

function showCreateDialog() {
  dialogMode.value = 'create'
  dialogVisible.value = true
}

function editUser(row) {
  dialogMode.value = 'edit'
  currentUserId.value = row.id
  userForm.username = row.username
  userForm.real_name = row.real_name
  userForm.role = row.role
  userForm.commission_rate = row.commission_rate || 10
  // 价格权限回显：后端逗号分隔字符串 → 数组；空/缺失视为全部可见
  userForm.price_permissions = row.price_permissions
    ? row.price_permissions.split(',').filter(Boolean)
    : ['cost_price', 'retail_price', 'min_price']
  userForm.is_active = row.is_active
  userForm.password = ''
  dialogVisible.value = true
}

async function submitUser() {
  if (!userFormRef.value) return

  try {
    await userFormRef.value.validate()
    submitting.value = true
    try {
      const data = {
        username: userForm.username,
        real_name: userForm.real_name,
        role: userForm.role,
        commission_rate: userForm.role === 'sales' ? userForm.commission_rate : null,
        // 价格权限：数组 → 逗号分隔字符串；全选时传空串（=全部可见）也可以，但显式传更清晰
        price_permissions: userForm.price_permissions.join(','),
        is_active: userForm.is_active
      }

      if (dialogMode.value === 'create') {
        data.password = userForm.password
        await usersStore.createUser(data)
        ElMessage.success('用户创建成功')
      } else {
        await usersStore.updateUserInfo(currentUserId.value, data)
        ElMessage.success('用户更新成功')
      }

      dialogVisible.value = false
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  } catch {
    // 表单验证未通过
  }
}

function resetForm() {
  userFormRef.value?.resetFields()
  userForm.username = ''
  userForm.real_name = ''
  userForm.password = ''
  userForm.role = 'sales'
  userForm.commission_rate = 10
  userForm.price_permissions = ['cost_price', 'retail_price', 'min_price']
  userForm.is_active = true
}

async function resetUserPassword(row) {
  try {
    await ElMessageBox.confirm(`确定要重置用户 ${row.username} 的密码吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const res = await resetPassword(row.id)
    ElMessage.success(res?.new_password ? `密码已重置，新密码: ${res.new_password}（请告知用户）` : '密码已重置')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重置密码失败')
    }
  }
}

async function handleDeleteUser(row) {
  try {
    await ElMessageBox.confirm(`确定要删除用户 ${row.username} 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await usersStore.deleteUserInfo(row.id)
    ElMessage.success('用户删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除用户失败')
    }
  }
}

// 初始化加载用户列表
usersStore.fetchUsers()
</script>

<style scoped>
.users-container {
  padding: 20px;
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

/* 左侧角色筛选面板 */
.role-panel {
  width: 200px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
}

.role-panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f2f5;
  margin-bottom: 8px;
}

.role-item {
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

.role-item:hover {
  background-color: #f5f7fa;
}

.role-item.active {
  background-color: #ecf5ff;
  color: #409eff;
  font-weight: 600;
}

.role-count {
  font-size: 11px;
  color: #a8abb2;
  background: #f0f2f5;
  border-radius: 10px;
  padding: 1px 8px;
}

.role-item.active .role-count {
  background: #409eff;
  color: #fff;
}

/* 右侧主区域 */
.users-main {
  flex: 1;
  min-width: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.role-filter-tip {
  font-size: 12px;
  color: #409eff;
  background: #ecf5ff;
  padding: 3px 10px;
  border-radius: 4px;
}

.price-perm-tip {
  width: 100%;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  margin-top: 2px;
}

@media (max-width: 900px) {
  .users-container {
    flex-direction: column;
  }
  .role-panel {
    width: 100%;
  }
}
</style>
