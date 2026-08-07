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
      </div>
      <div
        v-for="r in roleOptions"
        :key="r.value"
        class="role-item"
        :class="{ active: activeRole === r.value }"
        @click="selectRole(r.value)"
      >
        <span class="role-name">{{ r.label }}</span>
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
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" @closed="resetForm">
      <el-tabs v-model="activeFormTab" class="user-form-tabs">
        <!-- 模块一：基础信息 -->
        <el-tab-pane label="基础信息" name="basic">
          <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="100px">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="userForm.username" placeholder="请输入用户名" :disabled="dialogMode === 'edit'" />
            </el-form-item>
            <el-form-item label="真实姓名" prop="real_name">
              <el-input v-model="userForm.real_name" placeholder="请输入真实姓名" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="userForm.password"
                type="password"
                :placeholder="dialogMode === 'create' ? '请输入密码' : '留空则不修改密码'"
                show-password
              />
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
            <el-form-item label="启用状态">
              <el-switch v-model="userForm.is_active" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 模块二：价格权限 -->
        <el-tab-pane label="价格权限" name="price">
          <div class="price-perm-block">
            <div class="price-perm-row">
              <div class="price-perm-left">
                <el-checkbox-group v-model="userForm.price_permissions">
                  <el-checkbox value="cost_price">成本价</el-checkbox>
                  <el-checkbox value="retail_price">零售价</el-checkbox>
                  <el-checkbox value="min_price">最低售价</el-checkbox>
                </el-checkbox-group>
                <div class="price-perm-tip">
                  未勾选的价格，该账号在商品档案中显示为「***」；老板端不受此限制；新建用户默认不勾选（即默认全部价格不可见）。
                </div>
              </div>
              <div class="price-perm-right">
                <el-button type="primary" plain @click="openDataPermissionDialog">数据权限</el-button>
                <div class="price-perm-tip">配置类别 / 品牌 / 商品档案的增删改权限</div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 数据权限配置弹窗 -->
      <el-dialog v-model="dataPermDialogVisible" title="数据权限管理" width="560px">
        <div class="dp-module" v-for="m in dataPermModules" :key="m.key">
          <div class="dp-module-name">{{ m.label }}</div>
          <el-checkbox-group v-model="dataPermForm[m.key]">
            <el-checkbox value="add">新增</el-checkbox>
            <el-checkbox value="edit">修改</el-checkbox>
            <el-checkbox value="delete">删除</el-checkbox>
          </el-checkbox-group>
          <div class="dp-module-hint">{{ m.hint }}</div>
        </div>
        <div class="dp-tip">未勾选的操作，该账号在此模块看不到对应按钮、接口也会拒绝。老板端不受此限制。</div>
        <template #footer>
          <el-button @click="dataPermDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="dataPermDialogVisible = false">确定</el-button>
        </template>
      </el-dialog>

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
import { formatDateTime } from '@/utils/format'

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
// 新建/编辑对话框内的模块切换：basic=基础信息 / price=价格权限
const activeFormTab = ref('basic')

const userFormRef = ref(null)
const userForm = reactive({
  username: '',
  real_name: '',
  password: '',
  role: 'sales',
  commission_rate: 10,
  // 新建用户：价格权限默认不勾选（全部价格显示为 ***）；编辑时由 editUser 回显
  price_permissions: [],
  is_active: true
})

// ===== 数据权限（类别/品牌/商品档案 × 增删改） =====
const dataPermModules = [
  { key: 'category', label: '类别', hint: '类别管理页面的新增 / 修改 / 删除' },
  { key: 'brand', label: '品牌', hint: '品牌管理页面的新增 / 修改 / 删除' },
  { key: 'product', label: '商品档案', hint: '商品管理页面的新建 / 编辑 / 删除' }
]
const dataPermDialogVisible = ref(false)
// 数据权限表单：{ category: [], brand: [], product: [] }
const dataPermForm = reactive({ category: [], brand: [], product: [] })

function openDataPermissionDialog() {
  dataPermDialogVisible.value = true
}

// JSON 字符串 → 对象（编辑回显）
function parseDataPermissions(raw) {
  const out = { category: [], brand: [], product: [] }
  if (!raw) return out
  try {
    const o = typeof raw === 'string' ? JSON.parse(raw) : (raw || {})
    dataPermModules.forEach(m => {
      out[m.key] = Array.isArray(o[m.key]) ? o[m.key] : []
    })
  } catch (e) {
    /* 解析失败按无权限 */
  }
  return out
}

const userRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
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
  // 价格权限回显：后端逗号分隔字符串 → 数组；null/空=全不勾选（新行为）
  userForm.price_permissions = row.price_permissions
    ? row.price_permissions.split(',').filter(Boolean)
    : []
  // 数据权限回显：JSON → 对象
  const dp = parseDataPermissions(row.data_permissions)
  dataPermForm.category = dp.category
  dataPermForm.brand = dp.brand
  dataPermForm.product = dp.product
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
        // 数据权限：对象 → JSON 字符串（仅非空操作才写入；全空传空对象）
        data_permissions: JSON.stringify({
          category: dataPermForm.category,
          brand: dataPermForm.brand,
          product: dataPermForm.product
        }),
        is_active: userForm.is_active
      }

      if (dialogMode.value === 'create') {
        // 创建：密码必填
        if (!userForm.password) {
          ElMessage.warning('请输入密码')
          submitting.value = false
          return
        }
        data.password = userForm.password
        await usersStore.createUser(data)
        ElMessage.success('用户创建成功')
      } else {
        // 编辑：密码留空则不修改；填写则直接重置（无需原密码）
        if (userForm.password) {
          data.password = userForm.password
        }
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
  userForm.price_permissions = []
  dataPermForm.category = []
  dataPermForm.brand = []
  dataPermForm.product = []
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
    if (error !== 'cancel' && error !== 'close') {
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
    if (error !== 'cancel' && error !== 'close') {
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
  line-height: 1.6;
  margin-top: 10px;
}

/* 价格权限区左右布局（勾选框 | 数据权限按钮） */
.price-perm-row {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.price-perm-left {
  flex: 1;
  min-width: 220px;
}

.price-perm-right {
  flex: 0 0 auto;
  text-align: center;
  padding-top: 4px;
}

/* 数据权限配置弹窗 */
.dp-module {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 14px;
  background: #fafbfc;
}

.dp-module-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.dp-module-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

.dp-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 8px 12px;
}

/* 新建/编辑用户：两个平级模块（选项卡切换） */
.user-form-tabs {
  min-height: 260px;
}

.price-perm-block {
  padding: 20px 4px;
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
