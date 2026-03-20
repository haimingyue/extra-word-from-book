<template>
  <article class="metric-card soft-panel" :class="{ 'metric-card-accent': accent }">
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
  min-height: 182px;
  padding: 24px;
}

.metric-card-accent {
  background:
    linear-gradient(160deg, rgba(58, 141, 255, 0.92), rgba(77, 201, 170, 0.74)),
    var(--surface-1);
  color: var(--text-inverse);
}

.metric-label {
  color: var(--text-soft);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.metric-card-accent .metric-label,
.metric-card-accent p {
  color: rgba(245, 251, 255, 0.82);
}

strong {
  font-size: clamp(36px, 5vw, 54px);
  line-height: 0.96;
  letter-spacing: -0.05em;
}

p {
  margin: 0;
  color: var(--text-main);
  line-height: 1.7;
}
</style>
