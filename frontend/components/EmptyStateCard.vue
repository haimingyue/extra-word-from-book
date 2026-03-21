<template>
  <section class="empty-state surface-panel">
    <span class="eyebrow">{{ eyebrow }}</span>
    <div class="section-heading">
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="empty-actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  eyebrow?: string
  title: string
  description: string
}>()
</script>

<style scoped>
.empty-state {
  display: grid;
  gap: 18px;
  padding: 28px;
}

.empty-state h2 {
  font-size: clamp(28px, 4vw, 40px);
}

.empty-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 720px) {
  .empty-state {
    padding: 22px;
  }
}
</style>
