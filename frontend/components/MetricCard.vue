<template>
  <article class="metric-card surface-panel" :class="{ 'metric-card-accent': accent }">
    <span class="metric-label">{{ label }}</span>
    <strong>{{ value }}</strong>
    <p>{{ caption }}</p>
  </article>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  caption: string
  accent?: boolean
}>()
</script>

<style scoped>
.metric-card {
  display: grid;
  gap: 14px;
  min-height: 180px;
  padding: 24px;
  align-content: start;
}

.metric-card-accent {
  background: var(--surface-accent);
  color: var(--text-inverse);
  border: none;
}

.metric-label {
  color: var(--text-faint);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.metric-card-accent .metric-label,
.metric-card-accent p {
  color: rgba(255, 249, 245, 0.82);
}

strong {
  font-size: clamp(34px, 4vw, 52px);
  line-height: 0.94;
  letter-spacing: -0.05em;
}

p {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.75;
}
</style>
