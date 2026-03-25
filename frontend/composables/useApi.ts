type ApiEnvelope<T> = {
  code: string
  message: string
  data: T
}

export const useApi = () => {
  const config = useRuntimeConfig()
  const { token, clearAuth, openAuth } = useAuth()

  const formatValidationErrors = (detail: unknown) => {
    if (!Array.isArray(detail)) {
      return ''
    }

    const items = detail
      .map((item) => {
        const location = Array.isArray(item?.loc) ? item.loc.join('.') : ''
        const message = typeof item?.msg === 'string' ? item.msg : ''
        return [location, message].filter(Boolean).join(': ')
      })
      .filter(Boolean)

    return items.join('；')
  }

  const extractErrorMessage = (payload: any) => {
    if (!payload) {
      return ''
    }

    if (typeof payload?.message === 'string' && payload.message) {
      return payload.message
    }

    if (typeof payload?.detail === 'string' && payload.detail) {
      return payload.detail
    }

    const validationMessage = formatValidationErrors(payload?.detail)
    if (validationMessage) {
      return `请求参数错误：${validationMessage}`
    }

    return ''
  }

  const buildUrl = (path: string) => {
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path
    }
    if (path.startsWith('/api/')) {
      const apiRoot = new URL(config.public.apiBase)
      return `${apiRoot.origin}${path}`
    }
    return `${config.public.apiBase}${path}`
  }

  const request = async <T>(path: string, options: Parameters<typeof $fetch<ApiEnvelope<T>>>[1] = {}) => {
    try {
      const response = await $fetch<ApiEnvelope<T>>(buildUrl(path), {
        ...options,
        headers: {
          ...(options.headers || {}),
          ...(token.value ? { Authorization: `Bearer ${token.value}` } : {})
        }
      })
      return response.data
    } catch (error: any) {
      const payload = error?.data ?? error?.response?._data
      const message = extractErrorMessage(payload)
      if (message) {
        error.message = message
        error.data = {
          ...(payload && typeof payload === 'object' ? payload : {}),
          message
        }
      }

      const statusCode = error?.response?.status
      if (statusCode === 401) {
        clearAuth()
        openAuth('login')
      }
      throw error
    }
  }

  const downloadFile = async (path: string, filename: string) => {
    const response = await fetch(buildUrl(path), {
      headers: token.value ? { Authorization: `Bearer ${token.value}` } : {}
    })

    if (!response.ok) {
      throw new Error(`Download failed with status ${response.status}`)
    }

    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }

  return {
    request,
    downloadFile
  }
}
