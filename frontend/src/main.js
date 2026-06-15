import { createApp } from 'vue'
import ECharts from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
  GaugeChart,
  LineChart,
  BarChart,
  PieChart,
  ScatterChart,
  RadarChart
} from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  MarkLineComponent,
  MarkPointComponent,
  DataZoomComponent,
  VisualMapComponent,
  GraphicComponent,
  PolarComponent
} from 'echarts/components'
import App from './App.vue'
import './style.css'

use([
  CanvasRenderer,
  GaugeChart,
  LineChart,
  BarChart,
  PieChart,
  ScatterChart,
  RadarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  MarkLineComponent,
  MarkPointComponent,
  DataZoomComponent,
  VisualMapComponent,
  GraphicComponent,
  PolarComponent
])

const app = createApp(App)
app.component('v-chart', ECharts)
app.mount('#app')
