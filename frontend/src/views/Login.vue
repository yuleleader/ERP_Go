<template>
  <div class="login-container">
    <!-- 左侧：Logo 展示区（白色底，隐藏透明图的轻微光晕残留） -->
    <div class="login-brand">
      <img :src="logoUrl" alt="ERP_GO" class="brand-logo" />
    </div>
    <!-- 右侧：登录表单 -->
    <div class="login-panel">
      <div class="login-box">
        <h1 class="title">电商产销协同管理系统</h1>
        <el-form ref="loginFormRef" :model="loginForm" :rules="rules" class="login-form">
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="请输入用户名"
              prefix-icon="User"
              size="large"
              @keyup.enter="focusPassword"
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              ref="passwordInput"
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              prefix-icon="Lock"
              size="large"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              class="login-button"
              @click="handleLogin"
            >
              登 录
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessage } from 'element-plus'
import logoUrl from '@/assets/img/logo.png'

const router = useRouter()
const userStore = useUserStore()

const loginFormRef = ref(null)
const passwordInput = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

function focusPassword() {
  passwordInput.value?.focus()
}

async function handleLogin() {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
    loading.value = true
    try {
      await userStore.loginAction(loginForm)
      ElMessage.success('登录成功')
      // 默认管理员仍使用初始弱口令时，提醒修改密码
      if (loginForm.username === '1001' && loginForm.password === '1001') {
        ElMessage.warning('当前使用默认管理员密码，安全风险高，请尽快在【用户管理】中修改密码')
      }
      router.push('/')
    } catch (error) {
      console.error('Login error:', error)
      const errorMsg = error.response?.data?.detail || error.message || '登录失败'
      ElMessage.error(errorMsg)
    } finally {
      loading.value = false
    }
  } catch {
    // 表单验证未通过，不做任何处理
  }
}
</script>

<style scoped>
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
}

/* 左侧 Logo 区：纯白底，与 Logo 原图底色一致，透明残留的轻微光晕不可见 */
.login-brand {
  flex: 1;
  background: #ffffff;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

.brand-logo {
  width: 72%;
  max-width: 560px;
  height: auto;
  user-select: none;
  -webkit-user-drag: none;
}

/* 右侧登录区：品牌渐变底 + 白色表单卡片 */
.login-panel {
  width: 480px;
  min-width: 420px;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  width: 360px;
  padding: 40px;
  background: white;
  border-radius: 10px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.title {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
  font-size: 24px;
}

.login-form {
  width: 100%;
}

.login-button {
  width: 100%;
}

/* 窄屏适配：上下排布，Logo 缩小 */
@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
  }
  .login-brand {
    flex: none;
    padding: 24px 0;
  }
  .brand-logo {
    width: 45%;
    max-width: 220px;
  }
  .login-panel {
    width: 100%;
    min-width: 0;
    flex: 1;
  }
  .login-box {
    width: 86%;
    max-width: 360px;
  }
}
</style>
