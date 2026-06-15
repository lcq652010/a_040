<template>
  <div>
    <div class="metric-row">
      <div class="metric-card">
        <div class="metric-label">振动值</div>
        <div class="metric-value">
          {{ data?.latest?.vibration?.toFixed(3) || '--' }}
          <span class="metric-unit">mm/s</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-label">温度</div>
        <div class="metric-value">
          {{ data?.latest?.temperature?.toFixed(1) || '--' }}
          <span class="metric-unit">℃</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-label">电流</div>
        <div class="metric-value">
          {{ data?.latest?.current?.toFixed(2) || '--' }}
          <span class="metric-unit">A</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-label">转速</div>
        <div class="metric-value">
          {{ data?.latest?.speed?.toFixed(0) || '--' }}
          <span class="metric-unit">RPM</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-label">声发射</div>
        <div class="metric-value">
          {{ data?.latest?.acoustic?.toFixed(1) || '--' }}
          <span class="metric-unit">dB</span>
        </div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px;">
      <div>
        <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;padding-left:4px;display:flex;align-items:center;gap:8px;">
          <span style="width:3px;height:12px;background:linear-gradient(180deg,#1890ff,#13c2c2);border-radius:1px;"></span>
          振动频谱分析 (FFT)
        </div>
        <v-chart :option="spectrumOption" autoresize style="width:100%;height:300px;" />
      </div>

      <div style="display:grid;grid-template-rows:repeat(5, 1fr);gap:8px;">
        <div style="background:rgba(24,144,255,0.04);border:1px solid var(--border-color);border-radius:6px;padding:4px 8px;">
          <div style="font-size:10px;color:var(--text-muted);margin-bottom:2px;">振动趋势 (mm/s)</div>
          <v-chart :option="trendOption('vibration')" autoresize style="width:100%;height:46px;" />
        </div>
        <div style="background:rgba(250,173,20,0.04);border:1px solid var(--border-color);border-radius:6px;padding:4px 8px;">
          <div style="font-size:10px;color:var(--text-muted);margin-bottom:2px;">温度趋势 (℃)</div>
          <v-chart :option="trendOption('temperature')" autoresize style="width:100%;height:46px;" />
        </div>
        <div style="background:rgba(82,196,26,0.04);border:1px solid var(--border-color);border-radius:6px;padding:4px 8px;">
          <div style="font-size:10px;color:var(--text-muted);margin-bottom:2px;">电流趋势 (A)</div>
          <v-chart :option="trendOption('current')" autoresize style="width:100%;height:46px;" />
        </div>
        <div style="background:rgba(19,194,194,0.04);border:1px solid var(--border-color);border-radius:6px;padding:4px 8px;">
          <div style="font-size:10px;color:var(--text-muted);margin-bottom:2px;">转速趋势 (RPM)</div>
          <v-chart :option="trendOption('speed')" autoresize style="width:100%;height:46px;" />
        </div>
        <div style="background:rgba(114,46,209,0.04);border:1px solid var(--border-color);border-radius:6px;padding:4px 8px;">
          <div style="font-size:10px;color:var(--text-muted);margin-bottom:2px;">声发射趋势 (dB)</div>
          <v-chart :option="trendOption('acoustic')" autoresize style="width:100%;height:46px;" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, default: null }
})

const spectrumOption = computed(() => {
  const freq = props.data?.spectrum?.frequency || []
  const amp = props.data?.spectrum?.amplitude || []

  const peaks = []
  amp.forEach((v, i) => {
    if (v > 0.3 && i > 0 && i < amp.length - 1) {
      if (v > amp[i - 1] && v > amp[i + 1]) {
        peaks.push({
          coord: [freq[i], v],
          value: v
        })
      }
    }
  })
  const topPeaks = peaks.sort((a, b) => b.value - a.value).slice(0, 3).map(p => ({
    name: p.coord[0] + 'Hz',
    coord: p.coord,
    value: p.value,
    label: { show: true, formatter: p.coord[0] + 'Hz', position: 'top', fontSize: 10, color: '#91caff' }
  }))

  return {
    grid: { top: 20, right: 20, left: 50, bottom: 40 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(22,35,65,0.95)',
      borderColor: 'rgba(24,144,255,0.4)',
      textStyle: { color: '#e6f4ff', fontSize: 11 },
      formatter: (params) => {
        const p = params[0]
        return `频率: ${p.axisValue} Hz<br/>振幅: ${p.value.toFixed(4)}`
      }
    },
    xAxis: {
      type: 'category',
      name: '频率 (Hz)',
      nameLocation: 'middle',
      nameGap: 25,
      nameTextStyle: { color: '#5c7a99', fontSize: 11 },
      data: freq.filter((_, i) => i % 8 === 0),
      axisLabel: { color: '#5c7a99', fontSize: 10, interval: 0 },
      axisLine: { lineStyle: { color: 'rgba(24,144,255,0.2)' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      name: '振幅',
      nameTextStyle: { color: '#5c7a99', fontSize: 11 },
      axisLabel: { color: '#5c7a99', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(24,144,255,0.08)', type: 'dashed' } },
      axisLine: { show: false }
    },
    series: [{
      data: amp,
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#1890ff', width: 1.5, shadowColor: '#1890ff', shadowBlur: 5 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(24,144,255,0.5)' },
            { offset: 1, color: 'rgba(24,144,255,0.02)' }
          ]
        }
      }
    },
    {
      type: 'scatter',
      symbolSize: 8,
      symbol: 'pin',
      data: topPeaks,
      itemStyle: { color: '#ff4d4f', shadowColor: '#ff4d4f', shadowBlur: 10 },
      z: 10
    }]
  }
})

const metricColors = {
  vibration: '#1890ff',
  temperature: '#faad14',
  current: '#52c41a',
  speed: '#13c2c2',
  acoustic: '#722ed1'
}

const trendOption = (metric) => {
  const timestamps = props.data?.timestamps || []
  const values = props.data?.[metric] || []
  const color = metricColors[metric]

  return {
    grid: { left: 2, right: 2, top: 4, bottom: 2 },
    xAxis: { type: 'category', show: false, data: timestamps },
    yAxis: { type: 'value', show: false },
    series: [{
      data: values,
      type: 'line',
      smooth: true,
      symbol: 'none',
      showSymbol: false,
      lineStyle: { color: color, width: 1.2, shadowColor: color, shadowBlur: 3 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: color + '66' },
            { offset: 1, color: color + '05' }
          ]
        }
      }
    }]
  }
}
</script>
