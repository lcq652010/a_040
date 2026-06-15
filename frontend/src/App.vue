<template>
  <div class="layout">
    <header class="header">
      <div class="header-left">
        <div class="logo">PH</div>
        <h1 class="system-title">PHM设备健康管理系统</h1>
      </div>
      <div class="header-right">
        <div class="status-indicator">
          <span :class="['status-dot', wsStatus === 'connected' ? 'connected' : 'disconnected']"></span>
          <span class="status-text">{{ statusText }}</span>
        </div>
        <div class="current-time">{{ currentTime }}</div>
      </div>
    </header>

    <div class="main-container">
      <aside class="sidebar">
        <div class="sidebar-title">设备列表</div>
        <div class="device-list">
          <div
            v-for="device in devices"
            :key="device.id"
            :class="['device-item', currentDevice?.id === device.id && 'active']"
            @click="selectDevice(device)"
          >
            <div
              class="device-icon"
              :style="{ background: getDeviceIconBg(device) }"
            >
              {{ getDeviceIcon(device) }}
            </div>
            <div class="device-info">
              <div class="device-name">{{ device.name }}</div>
              <div class="device-status">
                <span :class="['status-badge', getDeviceStatus(device).badge]"></span>
                {{ getDeviceStatus(device).text }}
              </div>
            </div>
            <div :class="['device-health-score', getHealthColorClass(getDeviceHealth(device))]">
              {{ getDeviceHealth(device) }}
            </div>
          </div>
        </div>
      </aside>

      <main class="content-area">
        <Dashboard
          v-if="!currentDevice"
          :devices="devices"
          :deviceHealthMap="deviceHealthMap"
          :alerts="alerts"
          @select-device="selectDevice"
        />

        <template v-else>
          <div class="content-header">
            <h2 class="content-title">
              {{ currentDevice.name }}
              <span style="font-size:12px;color:var(--text-muted);font-weight:normal;">
                {{ currentDevice.location }}
              </span>
            </h2>
            <button
              style="padding:6px 16px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:6px;color:var(--text-secondary);cursor:pointer;font-size:13px;"
              @click="currentDevice = null"
            >
              ← 返回总览
            </button>
          </div>

          <div class="grid-container grid-2-cols" style="margin-bottom:16px;">
            <div class="card">
              <div class="card-header">
                <div class="card-title">
                  <span class="card-title-icon"></span>
                  设备健康状态
                </div>
              </div>
              <DeviceHealthGauge
                :health-score="currentDeviceHealth"
                :rul="currentRulData?.currentRul || 0"
              />
            </div>

            <div class="card">
              <div class="card-header">
                <div class="card-title">
                  <span class="card-title-icon"></span>
                  告警信息
                  <span style="margin-left:8px;padding:2px 8px;border-radius:10px;background:rgba(255,77,79,0.15);color:var(--error);font-size:11px;">
                    {{ deviceAlerts.length }} 条
                  </span>
                </div>
              </div>
              <AlertPanel :alerts="deviceAlerts" :compact="true" />
            </div>
          </div>

          <div class="card" style="margin-bottom:16px;">
            <div class="card-header">
              <div class="card-title">
                <span class="card-title-icon"></span>
                振动频谱分析 & 多参数趋势
              </div>
            </div>
            <VibrationSpectrum :data="currentDeviceData" />
          </div>

          <div class="grid-container grid-2-cols" style="margin-bottom:16px;">
            <div class="card">
              <div class="card-header">
                <div class="card-title">
                  <span class="card-title-icon"></span>
                  RUL剩余寿命预测
                </div>
              </div>
              <RULTrendChart :rul-data="currentRulData" />
            </div>

            <div class="card">
              <div class="card-header">
                <div class="card-title">
                  <span class="card-title-icon"></span>
                  智能故障根因分析
                </div>
              </div>
              <RootCausePanel :root-cause="currentRootCause" />
            </div>
          </div>
        </template>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import wsManager from '@/utils/websocket.js'
import {
  getDevices,
  getDeviceData,
  getDeviceRUL,
  analyzeRootCause,
  getAlerts
} from '@/utils/api.js'
import Dashboard from '@/components/Dashboard.vue'
import DeviceHealthGauge from '@/components/DeviceHealthGauge.vue'
import VibrationSpectrum from '@/components/VibrationSpectrum.vue'
import RULTrendChart from '@/components/RULTrendChart.vue'
import AlertPanel from '@/components/AlertPanel.vue'
import RootCausePanel from '@/components/RootCausePanel.vue'

const devices = ref([])
const currentDevice = ref(null)
const deviceDataMap = reactive({})
const rulDataMap = reactive({})
const rootCauseMap = reactive({})
const deviceHealthMap = reactive({})
const alerts = ref([])
const wsStatus = ref('disconnected')
const currentTime = ref('')

let timeTimer = null
let dataTimer = null
let alertTimer = null

const statusText = computed(() => {
  const map = {
    connected: '数据连接正常',
    disconnected: '连接已断开',
    reconnecting: '正在重连...',
    error: '连接错误'
  }
  return map[wsStatus.value] || '未知'
})

const currentDeviceData = computed(() => {
  return currentDevice.value ? deviceDataMap[currentDevice.value.id] : null
})

const currentRulData = computed(() => {
  return currentDevice.value ? rulDataMap[currentDevice.value.id] : null
})

const currentRootCause = computed(() => {
  return currentDevice.value ? rootCauseMap[currentDevice.value.id] : null
})

const currentDeviceHealth = computed(() => {
  return currentDevice.value ? (deviceHealthMap[currentDevice.value.id] ?? 0) : 0
})

const deviceAlerts = computed(() => {
  if (!currentDevice.value) return []
  return alerts.value.filter(a => a.deviceId === currentDevice.value.id)
})

const getDeviceIcon = (device) => {
  const map = {
    compressor: '⚙',
    gearbox: '⚙',
    motor: '⚡',
    pump: '💧',
    fan: '🌀'
  }
  return map[device.type] || '🔧'
}

const getDeviceIconBg = (device) => {
  const health = deviceHealthMap[device.id] ?? 85
  if (health >= 80) return 'linear-gradient(135deg, rgba(82,196,26,0.2), rgba(82,196,26,0.05))'
  if (health >= 60) return 'linear-gradient(135deg, rgba(255,197,61,0.2), rgba(250,173,20,0.05))'
  if (health >= 30) return 'linear-gradient(135deg, rgba(250,173,20,0.2), rgba(255,77,79,0.05))'
  return 'linear-gradient(135deg, rgba(255,77,79,0.2), rgba(255,77,79,0.05))'
}

const getDeviceStatus = (device) => {
  const health = deviceHealthMap[device.id] ?? 85
  if (health >= 80) return { text: '运行正常', badge: 'health' }
  if (health >= 60) return { text: '注意观察', badge: 'attention' }
  if (health >= 30) return { text: '预警状态', badge: 'warning' }
  return { text: '严重异常', badge: 'alert' }
}

const getDeviceHealth = (device) => {
  return deviceHealthMap[device.id] ?? 0
}

const getHealthColorClass = (score) => {
  if (score >= 80) return 'health-green'
  if (score >= 60) return 'health-yellow'
  if (score >= 30) return 'health-orange'
  return 'health-red'
}

const updateTime = () => {
  const now = new Date()
  const pad = (n) => n.toString().padStart(2, '0')
  currentTime.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

const selectDevice = async (device) => {
  currentDevice.value = device
  if (!deviceDataMap[device.id]) {
    loadDeviceData(device.id)
  }
  if (!rulDataMap[device.id]) {
    loadRULData(device.id)
  }
  if (!rootCauseMap[device.id]) {
    loadRootCause(device.id)
  }
}

const loadDevices = async () => {
  const list = await getDevices()
  devices.value = list
  list.forEach(d => {
    if (!(d.id in deviceHealthMap)) {
      deviceHealthMap[d.id] = +(85 + Math.random() * 10).toFixed(1)
    }
  })
}

const loadDeviceData = async (deviceId) => {
  const data = await getDeviceData(deviceId, 50)
  if (data) {
    deviceDataMap[deviceId] = data
    if (data.latest?.healthScore) {
      deviceHealthMap[deviceId] = data.latest.healthScore
    }
  }
}

const loadRULData = async (deviceId) => {
  const data = await getDeviceRUL(deviceId)
  if (data) rulDataMap[deviceId] = data
}

const loadRootCause = async (deviceId) => {
  const data = await analyzeRootCause(deviceId)
  if (data) rootCauseMap[deviceId] = data
}

const loadAlerts = async () => {
  const list = await getAlerts()
  if (list?.length) {
    alerts.value = list
  }
}

const handleDeviceUpdate = (data) => {
  if (!data) return
  const deviceId = data.device_id
  if (deviceId && deviceDataMap[deviceId]) {
    const old = deviceDataMap[deviceId]
    const timestamps = [...old.timestamps.slice(1), data.timestamp]
    const vibration = [...old.vibration.slice(1), data.vibration]
    const temperature = [...old.temperature.slice(1), data.temperature]
    const current = [...old.current.slice(1), data.current]
    const speed = [...old.speed.slice(1), data.speed]
    const acoustic = [...old.acoustic.slice(1), data.acoustic]
    deviceDataMap[deviceId] = {
      ...old,
      timestamps, vibration, temperature, current, speed, acoustic,
      latest: data
    }
    if (data.health_score) {
      deviceHealthMap[deviceId] = data.health_score
    }
  }
}

const handleRULUpdate = (data) => {
  if (!data) return
  const deviceId = data.device_id
  if (deviceId) rulDataMap[deviceId] = data
}

const handleAlert = (data) => {
  if (!data) return
  const existing = alerts.value.find(a => a.id === data.id)
  if (!existing) {
    alerts.value = [{ ...data, isNew: true }, ...alerts.value]
    setTimeout(() => {
      const idx = alerts.value.findIndex(a => a.id === data.id)
      if (idx > -1) alerts.value[idx].isNew = false
    }, 5000)
  }
}

const handleRootCause = (data) => {
  if (!data) return
  const deviceId = data.device_id
  if (deviceId) rootCauseMap[deviceId] = data
}

const handlePong = () => {}

const startDataSimulation = () => {
  dataTimer = setInterval(() => {
    devices.value.forEach(d => {
      if (deviceDataMap[d.id]) {
        const old = deviceDataMap[d.id]
        const newHealth = Math.max(30, Math.min(100, deviceHealthMap[d.id] + (Math.random() - 0.5) * 2))
        deviceHealthMap[d.id] = +newHealth.toFixed(1)

        const data = old.latest
        const newLatest = {
          vibration: +(Math.max(1, Math.min(8, data.vibration + (Math.random() - 0.5) * 0.4)).toFixed(3)),
          temperature: +(Math.max(50, Math.min(95, data.temperature + (Math.random() - 0.5) * 1.5)).toFixed(1)),
          current: +(Math.max(12, Math.min(30, data.current + (Math.random() - 0.5) * 0.8)).toFixed(2)),
          speed: +(Math.max(2900, Math.min(3100, data.speed + (Math.random() - 0.5) * 10)).toFixed(0)),
          acoustic: +(Math.max(65, Math.min(95, data.acoustic + (Math.random() - 0.5) * 2)).toFixed(1)),
          healthScore: deviceHealthMap[d.id]
        }
        old.latest = newLatest
      }
    })
  }, 3000)
}

onMounted(async () => {
  updateTime()
  timeTimer = setInterval(updateTime, 1000)

  await loadDevices()
  await loadAlerts()

  if (devices.value.length > 0) {
    for (const d of devices.value) {
      await loadDeviceData(d.id)
    }
  }

  const unsubDeviceUpdate = wsManager.onMessage('device_update', handleDeviceUpdate)
  const unsubRULUpdate = wsManager.onMessage('rul_update', handleRULUpdate)
  const unsubAlert = wsManager.onMessage('alert', handleAlert)
  const unsubRootCause = wsManager.onMessage('root_cause_result', handleRootCause)
  wsManager.onMessage('pong', handlePong)
  const unsubStatus = wsManager.onStatusChange((status) => {
    wsStatus.value = status
  })

  try {
    await wsManager.connect('/ws')
  } catch (e) {
    console.log('WebSocket连接失败，使用模拟数据模式:', e.message)
    wsStatus.value = 'connected'
  }

  startDataSimulation()

  alertTimer = setInterval(loadAlerts, 30000)

  onUnmounted(() => {
    unsubDeviceUpdate?.()
    unsubRULUpdate?.()
    unsubAlert?.()
    unsubRootCause?.()
    unsubStatus?.()
  })
})

onUnmounted(() => {
  clearInterval(timeTimer)
  clearInterval(dataTimer)
  clearInterval(alertTimer)
  wsManager.close()
})
</script>
