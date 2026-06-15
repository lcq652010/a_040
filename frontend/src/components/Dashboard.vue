<template>
  <div>
    <div class="content-header">
      <h2 class="content-title">总览仪表盘</h2>
      <div style="font-size:12px;color:var(--text-muted);">
        共 {{ devices.length }} 台设备在线监测
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card total">
        <div class="stat-icon">📊</div>
        <div class="stat-content">
          <div class="stat-value">{{ devices.length }}</div>
          <div class="stat-label">监测设备总数</div>
        </div>
      </div>
      <div class="stat-card normal">
        <div class="stat-icon">✓</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.normal }}</div>
          <div class="stat-label">正常运行</div>
        </div>
      </div>
      <div class="stat-card warning">
        <div class="stat-icon">⚠</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.warning }}</div>
          <div class="stat-label">预警设备</div>
        </div>
      </div>
      <div class="stat-card alert">
        <div class="stat-icon">✕</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.alert }}</div>
          <div class="stat-label">异常告警</div>
        </div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;">
      <div>
        <div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;padding-left:4px;">
          设备健康状态总览（点击卡片查看详情）
        </div>
        <div class="grid-container grid-5-cols">
          <div
            v-for="device in devices"
            :key="device.id"
            class="card dashboard-card"
            @click="$emit('select-device', device)"
          >
            <div class="dashboard-gauge">
              <v-chart :option="getMiniGaugeOption(device)" autoresize style="width:100%;height:180px;" />
            </div>
            <div class="dashboard-info">
              <div class="dashboard-device-name">{{ device.name }}</div>
              <div :class="['dashboard-status-text', getStatusColorClass(device)]">
                ● {{ getStatusText(device) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-title">
            <span class="card-title-icon"></span>
            全局告警
            <span :style="{
              marginLeft:'8px',
              padding:'2px 10px',
              borderRadius:'10px',
              background: alerts.length > 0 ? 'rgba(255,77,79,0.15)' : 'rgba(82,196,26,0.15)',
              color: alerts.length > 0 ? 'var(--error)' : 'var(--success)',
              fontSize:'11px',
              fontWeight:'500'
            }">
              {{ alerts.length }} 条
            </span>
          </div>
        </div>
        <div style="max-height:520px;overflow-y:auto;">
          <div v-if="!alerts.length" class="empty-state">
            <div class="empty-state-icon">✅</div>
            <div class="empty-state-text">暂无活动告警</div>
          </div>
          <div
            v-for="alert in alerts.slice(0, 8)"
            :key="alert.id"
            :class="['alert-item', alert.level, alert.isNew && 'new']"
          >
            <div class="alert-header">
              <div class="alert-device">{{ alert.deviceName }}</div>
              <span :class="['alert-level', alert.level]">{{ getAlertLevelText(alert.level) }}</span>
            </div>
            <div class="alert-time">{{ alert.time }}</div>
            <div class="alert-message">{{ alert.message }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  devices: { type: Array, default: () => [] },
  deviceHealthMap: { type: Object, default: () => ({}) },
  alerts: { type: Array, default: () => [] }
})

defineEmits(['select-device'])

const stats = computed(() => {
  let normal = 0, warning = 0, alert = 0
  props.devices.forEach(d => {
    const h = props.deviceHealthMap[d.id] ?? 85
    if (h >= 80) normal++
    else if (h >= 30) warning++
    else alert++
  })
  return { total: props.devices.length, normal, warning, alert }
})

const getHealth = (device) => props.deviceHealthMap[device.id] ?? 0

const getStatusColorClass = (device) => {
  const h = getHealth(device)
  if (h >= 80) return 'health-green'
  if (h >= 60) return 'health-yellow'
  if (h >= 30) return 'health-orange'
  return 'health-red'
}

const getStatusText = (device) => {
  const h = getHealth(device)
  if (h >= 80) return '正常'
  if (h >= 60) return '注意'
  if (h >= 30) return '预警'
  return '严重'
}

const getAlertLevelText = (level) => {
  const map = { severe: '严重', warning: '警告', attention: '注意' }
  return map[level] || level
}

const getMiniGaugeOption = (device) => {
  const value = getHealth(device)
  let color = '#52c41a'
  if (value < 30) color = '#ff4d4f'
  else if (value < 60) color = '#faad14'
  else if (value < 80) color = '#ffc53d'

  return {
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      radius: '95%',
      center: ['50%', '60%'],
      min: 0,
      max: 100,
      splitNumber: 5,
      progress: {
        show: true,
        width: 12,
        itemStyle: {
          color: color,
          shadowColor: color,
          shadowBlur: 10
        }
      },
      axisLine: {
        lineStyle: {
          width: 12,
          color: [
            [0.3, 'rgba(255,77,79,0.3)'],
            [0.6, 'rgba(250,173,20,0.3)'],
            [0.8, 'rgba(255,197,61,0.3)'],
            [1, 'rgba(82,196,26,0.3)']
          ]
        }
      },
      pointer: {
        show: true,
        length: '60%',
        width: 4,
        itemStyle: { color: color }
      },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      title: { show: false },
      detail: {
        valueAnimation: true,
        offsetCenter: [0, '5%'],
        fontSize: 26,
        fontWeight: 'bold',
        formatter: '{value}',
        color: color,
        fontFamily: 'Courier New, monospace'
      },
      data: [{ value: Math.round(value) }]
    }]
  }
}
</script>
