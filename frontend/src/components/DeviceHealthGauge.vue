<template>
  <div class="gauge-container">
    <v-chart :option="gaugeOption" autoresize style="width:100%;height:320px;" />
    <div class="gauge-info">
      <div :class="['gauge-status', statusColorClass]">{{ statusText }}</div>
      <div class="gauge-rul">
        剩余寿命 RUL: <span class="gauge-rul-value">{{ formatRUL(rul) }}</span> 小时
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  healthScore: { type: Number, default: 0 },
  rul: { type: Number, default: 0 }
})

const statusInfo = computed(() => {
  const s = props.healthScore
  if (s >= 90) return { text: '健康状态优秀', color: '#52c41a', class: 'health-green' }
  if (s >= 80) return { text: '运行状态良好', color: '#52c41a', class: 'health-green' }
  if (s >= 60) return { text: '注意观察趋势', color: '#ffc53d', class: 'health-yellow' }
  if (s >= 30) return { text: '预警状态需关注', color: '#faad14', class: 'health-orange' }
  return { text: '严重异常立即检修', color: '#ff4d4f', class: 'health-red' }
})

const statusText = computed(() => statusInfo.value.text)
const statusColorClass = computed(() => statusInfo.value.class)
const statusColor = computed(() => statusInfo.value.color)

const formatRUL = (val) => {
  if (val >= 10000) return (val / 1000).toFixed(1) + 'k'
  return val.toString()
}

const gaugeOption = computed(() => {
  const value = Math.round(props.healthScore)
  const color = statusColor.value

  return {
    series: [{
      type: 'gauge',
      startAngle: 225,
      endAngle: -45,
      radius: '100%',
      center: ['50%', '58%'],
      min: 0,
      max: 100,
      splitNumber: 10,
      progress: {
        show: true,
        width: 22,
        roundCap: true,
        clip: false,
        itemStyle: {
          color: color,
          shadowColor: color,
          shadowBlur: 20,
          opacity: 0.95
        }
      },
      axisLine: {
        lineStyle: {
          width: 22,
          color: [
            [0.3, 'rgba(255,77,79,0.25)'],
            [0.6, 'rgba(250,173,20,0.25)'],
            [0.8, 'rgba(255,197,61,0.25)'],
            [1, 'rgba(82,196,26,0.25)']
          ]
        }
      },
      pointer: {
        show: true,
        icon: 'path://M2.9,0.7L2.9,0.7c1.4,0,2.6,1.2,2.6,2.6v115c0,1.4-1.2,2.6-2.6,2.6l0,0c-1.4,0-2.6-1.2-2.6-2.6V3.3C0.3,1.9,1.5,0.7,2.9,0.7z',
        length: '72%',
        width: 6,
        offsetCenter: [0, '8%'],
        itemStyle: {
          color: color,
          shadowColor: color,
          shadowBlur: 15
        }
      },
      anchor: {
        show: true,
        size: 20,
        itemStyle: {
          color: color,
          borderColor: '#fff',
          borderWidth: 2,
          shadowColor: color,
          shadowBlur: 10
        }
      },
      axisTick: {
        distance: -32,
        length: 8,
        lineStyle: {
          color: 'rgba(255,255,255,0.4)',
          width: 1
        }
      },
      splitLine: {
        distance: -36,
        length: 14,
        lineStyle: {
          color: 'rgba(255,255,255,0.6)',
          width: 2
        }
      },
      axisLabel: {
        distance: -52,
        color: 'rgba(145,202,255,0.8)',
        fontSize: 11,
        fontFamily: 'Courier New, monospace'
      },
      title: {
        offsetCenter: [0, '35%'],
        fontSize: 12,
        color: '#5c7a99',
        fontWeight: 'normal'
      },
      detail: {
        valueAnimation: true,
        offsetCenter: [0, '-5%'],
        fontSize: 56,
        fontWeight: 'bold',
        fontFamily: 'Courier New, monospace',
        formatter: function (value) {
          return value
        },
        rich: {
          value: {
            lineHeight: 60
          }
        },
        color: color
      },
      data: [{
        value: value,
        name: 'HEALTH SCORE'
      }]
    }]
  }
})
</script>
