type AuthMode = 'login' | 'register'

type AuthUser = {
  user_id: number
  email: string
  display_name?: string | null
}

type LoginPayload = {
  email: string
  password: string
}

type RegisterPayload = LoginPayload & {
  display_name?: string
}

export const useAuth = () => {
  const token = useState<string>('auth-token', () => '')
  const currentUser = useState<AuthUser | null>('auth-user', () => null)
  const authVisible = useState<boolean>('auth-visible', () => false)
  const authMode = useState<AuthMode>('auth-mode', () => 'login')
  const pendingAction = useState<null | (() => Promise<void>)>('pending-auth-action', () => null)

  const initAuth = () => {
    if (!process.client) {
      return
    }
    token.value = localStorage.getItem('auth-token') || ''
    const rawUser = localStorage.getItem('auth-user')
    currentUser.value = rawUser ? JSON.parse(rawUser) as AuthUser : null
  }

  const persistAuth = (nextToken: string, user: AuthUser) => {
    token.value = nextToken
    currentUser.value = user
    if (process.client) {
      localStorage.setItem('auth-token', nextToken)
      localStorage.setItem('auth-user', JSON.stringify(user))
    }
  }

  const clearAuth = () => {
    token.value = ''
    currentUser.value = null
    if (process.client) {
      localStorage.removeItem('auth-token')
      localStorage.removeItem('auth-user')
    }
  }

  const openAuth = (mode: AuthMode = 'login', action?: () => Promise<void>) => {
    authMode.value = mode
    authVisible.value = true
    if (action) {
      pendingAction.value = action
    }
  }

  const closeAuth = () => {
    authVisible.value = false
  }

  const setPendingAction = (action: null | (() => Promise<void>)) => {
    pendingAction.value = action
  }

  const runPendingAction = async () => {
    if (!pendingAction.value) {
      return
    }
    const action = pendingAction.value
    pendingAction.value = null
    await action()
  }

  const config = useRuntimeConfig()

  const login = async (payload: LoginPayload) => {
    const response = await $fetch<{ code: string, message: string, data: { access_token: string, token_type: string, user: AuthUser } }>(
      `${config.public.apiBase}/auth/login`,
      {
        method: 'POST',
        body: payload
      }
    )
    persistAuth(response.data.access_token, response.data.user)
    return response.data.user
  }

  const register = async (payload: RegisterPayload) => {
    const response = await $fetch<{ code: string, message: string, data: AuthUser }>(
      `${config.public.apiBase}/auth/register`,
      {
        method: 'POST',
        body: payload
      }
    )
    return response.data
  }

  const isAuthenticated = computed(() => Boolean(token.value))
  const displayName = computed(() => currentUser.value?.display_name || currentUser.value?.email?.split('@')[0] || 'Learner')

  return {
    token,
    currentUser,
    isAuthenticated,
    displayName,
    authVisible,
    authMode,
    initAuth,
    openAuth,
    closeAuth,
    clearAuth,
    setPendingAction,
    runPendingAction,
    login,
    register
  }
}
