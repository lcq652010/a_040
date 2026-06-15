<template>
  <div class="chart-container medium">
    <v-chart :option="chartOption" autoresize style="width:100%;height:320px;" />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  rulData: { type: Object, default: null }
})

const chartOption = computed(() => {
  const history = props.rulData?.history || []
  const forecast = props.rulData?.forecast || []
  const warningThreshold = props.rulData?.warningThreshold || 60
  const criticalThreshold = props.rulData?.criticalThreshold || 30

  const allTimes = [
    ...history.map(h => h.time),
    ...forecast.map(f => f.time)
  ]

  const healthHistory = history.map(h => h.health)
  const healthForecast = forecast.map(f => f.health)
  const rulHistory = history.map(h => h.rul)
  const rulForecast = forecast.map(f => f.rul)

  const healthUpper = forecast.map(f => f.healthUpper)
  const healthLower = forecast.map(f => f.healthLower)

  const historyLen = history.length

  return {
    grid: { top: 50, right: 60, left: 50, bottom: 60 },
    legend: {
      top: 10,
      right: 10,
      textStyle: { color: '#91caff', fontSize: 11 },
      itemWidth: 16,
      itemHeight: 8,
      data: [
        { name: '健康度-历史' },
        { name: '健康度-预测' },
        { name: 'RUL-历史' },
        { name: 'RUL-预测' },
        { name: '预测区间' }
      ]
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(22,35,65,0.95)',
      borderColor: 'rgba(24,144,255,0.4)',
      textStyle: { color: '#e6f4ff', fontSize: 11 },
      axisPointer: {
        type: 'cross',
        lineStyle: { color: 'rgba(24,144,255,0.3)' }
      }
    },
    xAxis: {
      type: 'category',
      data: allTimes,
      boundaryGap: false,
      axisLabel: {
        color: '#5c7a99',
        fontSize: 10,
        rotate: 30,
        interval: Math.floor(allTimes.length / 8)
      },
      axisLine: { lineStyle: { color: 'rgba(24,144,255,0.2)' } },
      axisTick: { show: false }
    },
    yAxis: [
      {
        type: 'value',
        name: '健康度',
        nameTextStyle: { color: '#5c7a99', fontSize: 11, padding: [0, 40, 0, 0] },
        min: 0,
        max: 100,
        splitNumber: 5,
        position: 'left',
        axisLabel: { color: '#5c7a99', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(24,144,255,0.08)', type: 'dashed' } },
        axisLine: { show: false }
      },
      {
        type: 'value',
        name: 'RUL(小时)',
        nameTextStyle: { color: '#5c7a99', fontSize: 11 },
        min: 0,
        splitNumber: 5,
        position: 'right',
        axisLabel: { color: '#5c7a99', fontSize: 10 },
        splitLine: { show: false },
        axisLine: { show: false }
      }
    ],
    series: [
      {
        name: '健康度-历史',
        type: 'line',
        yAxisIndex: 0,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: healthHistory,
        lineStyle: { color: '#52c41a', width: 2.5, shadowColor: '#52c41a', shadowBlur: 8 },
        itemStyle: { color: '#52c41a', borderColor: '#fff', borderWidth: 1.5 }
      },
      {
        name: '健康度-预测',
        type: 'line',
        yAxisIndex: 0,
        smooth: true,
        symbol: 'diamond',
        symbolSize: 6,
        data: (new Array(historyLen - 1).fill(null)).concat(healthForecast),
        lineStyle: { color: '#52c41a', width: 2, type: 'dashed', shadowColor: '#52c41a', shadowBlur: 8 },
        itemStyle: { color: '#52c41a' }
      },
      {
        name: 'RUL-历史',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        data: rulHistory,
        lineStyle: { color: '#1890ff', width: 2.5, shadowColor: '#1890ff', shadowBlur: 8 },
        itemStyle: { color: '#1890ff', borderColor: '#fff', borderWidth: 1.5 }
      },
      {
        name: 'RUL-预测',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'diamond',
        symbolSize: 5,
        data: (new Array(historyLen - 1).fill(null)).concat(rulForecast),
        lineStyle: { color: '#1890ff', width: 2, type: 'dashed', shadowColor: '#1890ff', shadowBlur: 8 },
        itemStyle: { color: '#1890ff' }
      },
      {
        name: '预测区间',
        type: 'line',
        yAxisIndex: 0,
        symbol: 'none',
        data: (new Array(historyLen - 1).fill(null)).concat(healthUpper),
        lineStyle: { opacity: 0 },
        stack: 'confidence-band'
      },
      {
        type: 'line',
        yAxisIndex: 0,
        symbol: 'none',
        data: (new Array(historyLen - 1).fill(null)).concat(healthLower),
        lineStyle: { opacity: 0 },
        stack: 'confidence-band',
        areaStyle: {
          color: 'rgba(82,196,26,0.15)'
        },
        z: -1
      },
      {
        type: 'line',
        yAxisIndex: 0,
        markLine: {
          symbol: 'none',
          silent: true,
          data: [
            {
              yAxis: warningThreshold,
              lineStyle: { color: '#faad14', type: 'dashed', width: 1.5 },
              label: {
                formatter: '预警线 ' + warningThreshold,
                position: 'end',
                color: '#faad14',
                fontSize: 10,
                backgroundColor: 'rgba(250,173,20,0.1)',
                padding: [2, 6]
              }
            },
            {
              yAxis: criticalThreshold,
              lineStyle: { color: '#ff4d4f', type: 'dashed', width: 1.5 },
              label: {
                formatter: '危险线 ' + criticalThreshold,
                position: 'end',
                color: '#ff4d4f',
                fontSize: 10,
                backgroundColor: 'rgba(255,77,79,0.1)',
                padding: [2, 6]
              }
            }
          ]
        }
      }
    ]
  }
})
</script>
