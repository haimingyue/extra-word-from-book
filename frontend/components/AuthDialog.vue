<template>
  <el-dialog
    :model-value="authVisible"
    width="520px"
    align-center
    class="auth-dialog"
    @close="closeAuth"
  >
    <template #header>
      <div class="auth-header">
        <div class="auth-badge soft-pill">
          <span>{{ authMode === 'login' ? 'Welcome Back' : 'Start Learning' }}</span>
        </div>
        <h2>{{ authMode === 'login' ? '登录后继续你的学习流程' : '创建账号，保存你的学习进度' }}</h2>
        <p>登录注册都在这里完成，成功后会自动回到你刚才的操作。</p>
      </div>
    </template>

    <el-tabs v-model="tabValue" stretch class="auth-tabs">
      <el-tab-pane label="登录" name="login">
        <el-form :model="loginForm" label-position="top" @submit.prevent="submitLogin">
          <el-form-item label="邮箱">
            <el-input v-model="loginForm.email" placeholder="alice@example.com" size="large" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入密码" size="large" />
          </el-form-item>
          <el-button
            type="primary"
            round
            size="large"
            class="auth-submit"
            :loading="submitting"
            @click="submitLogin"
          >
            登录并继续
          </el-button>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="注册" name="register">
        <el-form :model="registerForm" label-position="top" @submit.prevent="submitRegister">
          <el-form-item label="昵称">
            <el-input v-model="registerForm.display_name" placeholder="你的学习昵称" size="large" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="registerForm.email" placeholder="alice@example.com" size="large" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="registerForm.password" type="password" show-password placeholder="至少 8 位更稳妥" size="large" />
          </el-form-item>
          <el-button
            type="primary"
            round
            size="large"
            class="auth-submit"
            :loading="submitting"
            @click="submitRegister"
          >
            创建账号
          </el-button>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

const {
  authVisible,
  authMode,
  closeAuth,
  login,
  register,
  runPendingAction
} = useAuth()

const tabValue = computed({
  get: () => authMode.value,
  set: (value) => {
    authMode.value = value as 'login' | 'register'
  }
})

const submitting = ref(false)
const loginForm = reactive({
  email: '',
  password: ''
})

const registerForm = reactive({
  display_name: '',
  email: '',
  password: ''
})

const submitLogin = async () => {
  if (!loginForm.email || !loginForm.password) {
    ElMessage.warning('请先填写邮箱和密码')
    return
  }

  submitting.value = true
  try {
    await login(loginForm)
    ElMessage.success('登录成功')
    closeAuth()
    await runPendingAction()
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '登录失败')
  } finally {
    submitting.value = false
  }
}

const submitRegister = async () => {
  if (!registerForm.email || !registerForm.password) {
    ElMessage.warning('请先填写邮箱和密码')
    return
  }

  submitting.value = true
  try {
    await register(registerForm)
    await login({
      email: registerForm.email,
      password: registerForm.password
    })
    ElMessage.success('注册成功，已自动登录')
    closeAuth()
    await runPendingAction()
  } catch (error: any) {
    ElMessage.error(error?.data?.message || error?.message || '注册失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.auth-header {
  display: grid;
  gap: 12px;
  padding-right: 32px;
}

.auth-badge {
  width: fit-content;
  padding: 8px 14px;
  color: var(--primary-600);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.auth-header h2 {
  margin: 0;
  font-size: clamp(24px, 3vw, 34px);
  line-height: 1.08;
  letter-spacing: -0.03em;
}

.auth-header p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.7;
}

.auth-submit {
  width: 100%;
  margin-top: 8px;
  min-height: 52px;
}

.auth-tabs {
  margin-top: 4px;
}
</style>
