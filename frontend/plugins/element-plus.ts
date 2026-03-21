import ElementPlus from 'element-plus'
import { ID_INJECTION_KEY } from 'element-plus/es/hooks/use-id/index.mjs'
import { ZINDEX_INJECTION_KEY } from 'element-plus/es/hooks/use-z-index/index.mjs'

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.provide(ID_INJECTION_KEY, {
    prefix: 0,
    current: 0
  })
  nuxtApp.vueApp.provide(ZINDEX_INJECTION_KEY, {
    current: 0
  })
  nuxtApp.vueApp.use(ElementPlus)
})
