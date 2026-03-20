<template>
  <NuxtLayout>
    <NuxtPage />
    <AuthDialog />
  </NuxtLayout>
</template>

<script setup lang="ts">
const { initAuth } = useAuth()
const { initTheme } = useTheme()
const { initUserPreferences } = useUserPreferences()

onMounted(() => {
  initAuth()
  initTheme()
  initUserPreferences()
})
</script>
