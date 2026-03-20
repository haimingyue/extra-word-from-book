<template>
  <NuxtLayout>
    <NuxtPage />
    <AuthDialog />
  </NuxtLayout>
</template>

<script setup lang="ts">
const { initAuth } = useAuth()
const { initTheme } = useTheme()

onMounted(() => {
  initAuth()
  initTheme()
})
</script>
