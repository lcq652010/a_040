<template>
  <div v-if="!alerts.length" class="empty-state" :style="compact && { padding: '32px' }">
    <div class="empty-state-icon">✅</div>
    <div class="empty-state-text">暂无活动告警</div>
  </div>

  <div v-else class="alert-list" :style="compact && { maxHeight: '320px' }">
    <div
      v-for="alert in alerts"
      :key="alert.id"
      :class="['alert-item', alert.level, alert.isNew && 'new']"
    >
      <div class="alert-header">
        <div class="alert-device">
          <span :style="{ marginRight:'6px', fontSize:'12px' }">{{ getLevelIcon(alert.level) }}</span>
          {{ alert.deviceName }}
        </div>
        <span :class="['alert-level', alert.level]">{{ getLevelText(alert.level) }}</span>
      </div>
      <div class="alert-time">{{ alert.time }}</div>
      <div class="alert-message">{{ alert.message }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  alerts: { type: Array, default: () => [] },
  compact: { type: Boolean, default: false }
})

const getLevelIcon = (level) => {
  const map = { severe: '🔴', warning: '🟠', attention: '🟡' }
  return map[level] || '⚪'
}

const getLevelText = (level) => {
  const map = { severe: '严重', warning: '警告', attention: '注意' }
  return map[level] || level
}
</script>
