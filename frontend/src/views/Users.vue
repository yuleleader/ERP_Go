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
            <el-button v-if="canAdd" type="primary" @click="showCreateDialog">新建用户</el-button>
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
              <el-button v-if="canEdit" link type="primary" size="small" @click="editUser(row)">编辑</el-button>
              <el-button v-if="canEdit" link type="warning" size="small" @click="resetUserPassword(row)">重置密码</el-button>
              <el-button v-if="canDelete" link type="danger" size="small" @click="handleDeleteUser(row)">删除</el-button>
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
            <el-checkbox-group v-model="userForm.price_permissions">
              <el-checkbox value="cost_price">成本价</el-checkbox>
              <el-checkbox value="retail_price">零售价</el-checkbox>
              <el-checkbox value="min_price">最低售价</el-checkbox>
            </el-checkbox-group>
            <div class="price-perm-tip">
              未勾选的价格，该账号在商品档案中显示为「***」；老板端不受此限制；新建用户默认不勾选（即默认全部价格不可见）。
            </div>
          </div>
        </el-tab-pane>

        <!-- 模块三：数据权限（全模块树形；与价格权限平级） -->
        <el-tab-pane label="数据权限" name="dataPermission">
          <div class="data-perm-block">
            <div class="perm-toolbar">
              <el-button size="small" @click="setAllExpanded(true)">一键展开</el-button>
              <el-button size="small" @click="setAllExpanded(false)">一键收缩</el-button>
              <el-button size="small" type="primary" plain @click="setAllChecked(true)">全选（全页面）</el-button>
              <el-button size="small" @click="setAllChecked(false)">清空</el-button>
            </div>
            <div class="data-perm-tip">勾选「查询」该页面才会显示菜单；未勾选查询时，该页面的新增 / 修改 / 删除 / 导出自动失效。老板端不受限制，始终可见全部。</div>
            <div class="perm-tree">
              <div class="perm-module" v-for="mod in PERM_TREE" :key="mod.key">
                <div class="perm-module-head">
                  <el-icon class="perm-arrow" :class="{ open: expanded[mod.key] }" @click="toggleModule(mod.key)"><ArrowRight /></el-icon>
                  <span class="perm-module-title" @click="toggleModule(mod.key)">{{ mod.title }}</span>
                  <el-checkbox
                    class="perm-select-all"
                    :model-value="moduleState(mod).checked"
                    :indeterminate="moduleState(mod).indeterminate"
                    @change="(v) => setModuleAll(mod, v)"
                  >全选</el-checkbox>
                </div>
                <div v-show="expanded[mod.key]" class="perm-module-body">
                  <template v-if="mod.pages">
                    <div class="perm-page" v-for="p in mod.pages" :key="p.path">
                      <div class="perm-page-name">{{ p.label }}</div>
                      <el-checkbox-group
                        :model-value="permForm[p.path]"
                        @change="(v) => onPageChange(p, v)"
                      >
                        <el-checkbox
                          v-for="a in p.actions"
                          :key="a"
                          :value="a"
                          :disabled="a !== 'query' && !hasQuery(p)"
                        >{{ ACTION_LABELS[a] }}</el-checkbox>
                      </el-checkbox-group>
                    </div>
                  </template>
                  <template v-else>
                    <div class="perm-group" v-for="g in mod.groups" :key="g.title">
                      <div class="perm-group-head">
                        <span>{{ g.title }}</span>
                        <el-checkbox
                          class="perm-select-all"
                          :model-value="groupState(g).checked"
                          :indeterminate="groupState(g).indeterminate"
                          @change="(v) => setGroupAll(g, v)"
                        >全选</el-checkbox>
                      </div>
                      <div class="perm-page" v-for="p in g.pages" :key="p.path">
                        <div class="perm-page-name">{{ p.label }}</div>
                        <el-checkbox-group
                          :model-value="permForm[p.path]"
                          @change="(v) => onPageChange(p, v)"
                        >
                          <el-checkbox
                            v-for="a in p.actions"
                            :key="a"
                            :value="a"
                            :disabled="a !== 'query' && !hasQuery(p)"
                          >{{ ACTION_LABELS[a] }}</el-checkbox>
                        </el-checkbox-group>
                      </div>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitUser" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'Users' })
import { ref, reactive, computed } from 'vue'
import { useUsersStore } from '@/store/users'
import { useUserStore } from '@/store/user'
import { checkDataPerm } from '@/utils/dataPerm'
import { resetPassword } from '@/api/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/format'
import { PERM_TREE, ACTION_LABELS, modulePages, allPages, normalizePerms } from '@/utils/permTree'

const usersStore = useUsersStore()
const userStore = useUserStore()
const canAdd = computed(() => checkDataPerm(userStore.userInfo, '/users', 'add'))
const canEdit = computed(() => checkDataPerm(userStore.userInfo, '/users', 'edit'))
const canDelete = computed(() => checkDataPerm(userStore.userInfo, '/users', 'delete'))
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
// 新建/编辑对话框内的模块切换：basic=基础信息 / price=价格权限 / dataPermission=数据权限
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

// ===== 数据权限（全模块树形：一级模块 → 分组 → 页面 × 按性质定制操作） =====
// 权限表单：{ path: [操作码...] }；新建账号默认全空（任何勾选都必须由创建者显式打开）
const permForm = reactive({})
allPages().forEach((p) => { permForm[p.path] = [] })

// 一级模块展开状态：默认全部展开
const expanded = reactive({})
PERM_TREE.forEach((mod) => { expanded[mod.key] = true })

function toggleModule(key) { expanded[key] = !expanded[key] }
function setAllExpanded(v) { PERM_TREE.forEach((m) => { expanded[m.key] = v }) }

// 页面是否已勾「查询」
function hasQuery(page) { return (permForm[page.path] || []).includes('query') }

// 页面勾选变更：未勾「查询」时其余操作全部清空（增删改导出同步失效）
function onPageChange(page, val) {
  const arr = val || []
  permForm[page.path] = arr.includes('query') ? arr : []
}

function pageCheckedCount(page) {
  return (permForm[page.path] || []).filter((a) => page.actions.includes(a)).length
}

function groupState(group) {
  let total = 0, checked = 0
  group.pages.forEach((p) => { total += p.actions.length; checked += pageCheckedCount(p) })
  return { checked: total > 0 && checked === total, indeterminate: checked > 0 && checked < total }
}

function moduleState(mod) {
  const pages = modulePages(mod)
  let total = 0, checked = 0
  pages.forEach((p) => { total += p.actions.length; checked += pageCheckedCount(p) })
  return { checked: total > 0 && checked === total, indeterminate: checked > 0 && checked < total }
}

function setGroupAll(group, v) {
  group.pages.forEach((p) => { permForm[p.path] = v ? [...p.actions] : [] })
}

function setModuleAll(mod, v) {
  modulePages(mod).forEach((p) => { permForm[p.path] = v ? [...p.actions] : [] })
}

function setAllChecked(v) {
  allPages().forEach((p) => { permForm[p.path] = v ? [...p.actions] : [] })
}

// JSON 字符串/对象 → 权限表单（编辑回显，兼容旧格式）
function parseDataPermissions(raw) {
  const o = normalizePerms(raw)
  allPages().forEach((p) => { permForm[p.path] = Array.isArray(o[p.path]) ? o[p.path] : [] })
}

// 全部权限归零（新建账号时使用）
function resetDataPermissions() {
  allPages().forEach((p) => { permForm[p.path] = [] })
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
  currentUserId.value = null
  // 新建账号：重置全部表单字段为默认值，确保价格权限 / 数据权限"默认不勾选"
  // （如果不重置，会沿用上次编辑账号时残留的勾选）
  userForm.username = ''
  userForm.real_name = ''
  userForm.password = ''
  userForm.role = 'sales'
  userForm.commission_rate = 10
  userForm.price_permissions = []
  userForm.is_active = true
  resetDataPermissions()
  activeFormTab.value = 'basic'
  dialogVisible.value = true
}

function editUser(row) {
  dialogMode.value = 'edit'
  currentUserId.value = row.id
  activeFormTab.value = 'basic'
  userForm.username = row.username
  userForm.real_name = row.real_name
  userForm.role = row.role
  userForm.commission_rate = row.commission_rate || 10
  // 价格权限回显：后端逗号分隔字符串 → 数组；null/空=全不勾选（新行为）
  userForm.price_permissions = row.price_permissions
    ? row.price_permissions.split(',').filter(Boolean)
    : []
  // 数据权限回显：JSON → 权限表单（全模块树形）
  parseDataPermissions(row.data_permissions)
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
        // 数据权限：权限表单（{path:[操作码]}）→ JSON 字符串（仅非空操作才写入；全空传空对象）
        data_permissions: JSON.stringify(
          Object.fromEntries(
            Object.entries(permForm).filter(([, v]) => Array.isArray(v) && v.length)
          )
        ),
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
  resetDataPermissions()
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

/* 数据权限（全模块树形，独立 tab，与价格权限平级） */
.data-perm-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.perm-toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.data-perm-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}

/* 树形主体：超出部分滚动（弹窗尺寸保持不变） */
.perm-tree {
  max-height: 330px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
  padding: 4px 0;
}

.perm-module {
  border-bottom: 1px solid #f0f2f5;
}
.perm-module:last-child {
  border-bottom: none;
}

.perm-module-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  background: #f7f9fc;
  cursor: pointer;
  user-select: none;
}

.perm-arrow {
  font-size: 13px;
  color: #909399;
  transition: transform 0.2s;
}
.perm-arrow.open {
  transform: rotate(90deg);
}

.perm-module-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  flex: 1;
}

.perm-select-all {
  margin-right: 0;
}

.perm-module-body {
  padding: 6px 12px 10px 26px;
}

.perm-group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 4px 4px;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.perm-page {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 7px 4px;
  border-top: 1px dashed #f0f2f5;
}

.perm-page-name {
  font-size: 13px;
  color: #303133;
  white-space: nowrap;
}

.perm-page .el-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.perm-page .el-checkbox {
  margin-right: 16px;
}
.perm-page .el-checkbox:last-child {
  margin-right: 0;
}

/* 第三个 tab"数据权限"红色字体（与价格权限平级，提醒注意） */
.user-form-tabs .el-tabs__item:nth-child(3) {
  color: #f56c6c;
}

.user-form-tabs .el-tabs__item:nth-child(3):hover {
  color: #f56c6c;
}

.user-form-tabs .el-tabs__item:nth-child(3).is-active {
  color: #f56c6c;
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
