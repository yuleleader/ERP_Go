<template>
  <div class="login-container">
    <!-- 装饰性光斑（纯 CSS，不占布局） -->
    <div class="deco deco-1"></div>
    <div class="deco deco-2"></div>
    <div class="deco deco-3"></div>

    <!-- 左侧：品牌 Logo（白色圆角卡片衬托，渐变底上更精致） -->
    <div class="login-brand">
      <div class="brand-card">
        <img :src="logoUrl" alt="ERP_GO" class="brand-logo" />
      </div>
      <p class="brand-slogan">电商产销协同管理系统</p>
    </div>

    <!-- 右侧：登录表单 -->
    <div class="login-panel">
      <div class="login-box">
        <h1 class="title">欢迎登录</h1>
        <p class="subtitle">请输入您的账号信息以继续</p>
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
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #5b7cfa 0%, #7c5ce7 50%, #9b59d0 100%);
}

/* ── 装饰光斑 ── */
.deco {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}

.deco-1 {
  top: -18%;
  left: -8%;
  width: 42vw;
  height: 42vw;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.16) 0%, transparent 62%);
}

.deco-2 {
  bottom: -22%;
  right: 12%;
  width: 46vw;
  height: 46vw;
  background: radial-gradient(circle, rgba(64, 224, 208, 0.14) 0%, transparent 60%);
}

.deco-3 {
  top: 22%;
  right: -6%;
  width: 26vw;
  height: 26vw;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.10) 0%, transparent 60%);
}

/* ── 左侧品牌区 ── */
.login-brand {
  flex: 1.15;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 26px;
  z-index: 1;
  padding: 40px;
}

.brand-card {
  background: #ffffff;
  border-radius: 28px;
  padding: 52px 56px;
  box-shadow: 0 25px 60px rgba(20, 30, 70, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
  max-width: 640px;
  width: 88%;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.brand-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 32px 70px rgba(20, 30, 70, 0.34);
}

.brand-logo {
  width: 100%;
  max-width: 500px;
  height: auto;
  user-select: none;
  -webkit-user-drag: none;
}

.brand-slogan {
  margin: 0;
  color: rgba(255, 255, 255, 0.92);
  font-size: 18px;
  letter-spacing: 2px;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
}

/* ── 右侧登录区 ── */
.login-panel {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1;
  padding: 40px;
}

.login-box {
  width: 380px;
  padding: 44px 40px 36px;
  background: rgba(255, 255, 255, 0.97);
  border-radius: 20px;
  box-shadow: 0 18px 50px rgba(20, 30, 70, 0.30);
}

.title {
  text-align: center;
  margin: 0 0 6px;
  color: #2d3436;
  font-size: 26px;
  font-weight: 700;
}

.subtitle {
  text-align: center;
  margin: 0 0 30px;
  color: #9aa5b1;
  font-size: 14px;
}

.login-form {
  width: 100%;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 10px;
  padding: 2px 14px;
}

.login-button {
  width: 100%;
  height: 46px;
  font-size: 16px;
  letter-spacing: 6px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(90deg, #5b7cfa 0%, #7c5ce7 100%);
  box-shadow: 0 8px 20px rgba(92, 107, 250, 0.35);
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.login-button:hover {
  opacity: 0.92;
  transform: translateY(-1px);
}

/* ── 窄屏适配：上下排布 ── */
@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
  }

  .login-brand {
    flex: none;
    padding: 36px 24px 8px;
    gap: 18px;
  }

  .brand-card {
    padding: 28px 32px;
    width: 74%;
    border-radius: 20px;
  }

  .brand-slogan {
    font-size: 15px;
  }

  .login-panel {
    width: 100%;
    padding: 16px 20px 40px;
  }

  .login-box {
    width: 100%;
    max-width: 380px;
    padding: 32px 26px 26px;
  }
}
</style>
