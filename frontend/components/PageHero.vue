<template>
  <section class="page-hero surface-panel" :class="{ 'page-hero-accent': accent }">
    <div class="hero-main">
      <span v-if="eyebrow" class="eyebrow" :class="{ 'eyebrow-inverse': accent }">{{ eyebrow }}</span>
      <div class="section-heading">
        <h1>{{ title }}</h1>
        <p>{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="hero-actions">
        <slot name="actions" />
      </div>
    </div>

    <div v-if="stats?.length" class="hero-stats">
      <article v-for="stat in stats" :key="stat.label" class="stat-tile">
        <strong>{{ stat.value }}</strong>
        <span>{{ stat.label }}</span>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  eyebrow?: string
  title: string
  description: string
  stats?: Array<{ label: string; value: string | number }>
  accent?: boolean
}>()
</script>

<style scoped>
.page-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
  gap: 28px;
  padding: 30px;
}

.page-hero-accent {
  background:
    linear-gradient(135deg, rgba(255, 125, 87, 0.94), rgba(255, 180, 107, 0.94)),
    var(--surface-panel);
  color: var(--text-inverse);
  border: none;
}

.hero-main {
  display: grid;
  gap: 18px;
}

.hero-main h1 {
  font-size: clamp(38px, 5vw, 64px);
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.hero-stats {
  display: grid;
  gap: 14px;
}

.stat-tile {
  display: grid;
  gap: 6px;
  padding: 18px 20px;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.1);
}

.page-hero:not(.page-hero-accent) .stat-tile {
  background: var(--surface-soft);
  border-color: var(--border-soft);
}

.stat-tile strong {
  font-size: 28px;
  line-height: 1;
}

.stat-tile span {
  color: inherit;
  opacity: 0.78;
}

.eyebrow-inverse {
  color: rgba(255, 249, 245, 0.92);
  background: rgba(255, 255, 255, 0.12);
}

@media (max-width: 980px) {
  .page-hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .page-hero {
    padding: 22px;
  }

  .hero-main h1 {
    font-size: 38px;
  }
}
</style>
