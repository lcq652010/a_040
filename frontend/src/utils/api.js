import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

request.interceptors.request.use(
  config => {
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('响应错误:', error.message)
    return Promise.reject(error)
  }
)

export const getDevices = async () => {
  try {
    const data = await request.get('/devices')
    if (data?.devices) return data.devices
    if (Array.isArray(data?.data)) return data.data
    if (Array.isArray(data)) return data
    throw new Error('no data')
  } catch {
    return [
      { device_id: 'AC-001', device_name: '空压机', device_type: 'air_compressor', location: '动力车间-A区', status: 'running' },
      { device_id: 'CP-001', device_name: '离心泵', device_type: 'centrifugal_pump', location: '供水车间-1号泵站', status: 'running' },
      { device_id: 'FN-001', device_name: '风机', device_type: 'fan', location: '通风车间-主风机房', status: 'running' },
      { device_id: 'CV-001', device_name: '传送带', device_type: 'conveyor', location: '装配车间-2号线', status: 'running' },
      { device_id: 'CT-001', device_name: '冷却塔', device_type: 'cooling_tower', location: '冷却系统-室外平台', status: 'running' }
    ]
  }
}

export const getDeviceData = async (deviceId, limit = 50) => {
  try {
    const data = await request.get(`/devices/${deviceId}/data?limit=${limit}`)
    return data?.data || data || null
  } catch {
    return generateMockDeviceData(deviceId, limit)
  }
}

export const getDeviceRUL = async (deviceId) => {
  try {
    const data = await request.get(`/devices/${deviceId}/rul`)
    return data?.data || data || null
  } catch {
    return generateMockRULData(deviceId)
  }
}

export const analyzeRootCause = async (deviceId) => {
  try {
    const data = await request.post(`/devices/${deviceId}/root-cause`)
    return data?.data || data || []
  } catch {
    return generateMockRootCause(deviceId)
  }
}

export const getAlerts = async (deviceId = null, limit = 50) => {
  try {
    const url = deviceId ? `/devices/${deviceId}/alerts?limit=${limit}` : `/alerts?limit=${limit}`
    const data = await request.get(url)
    return data?.data || data || []
  } catch {
    return generateMockAlerts(deviceId)
  }
}

const generateMockDeviceData = (deviceId, limit) => {
  const now = Date.now()
  const timestamps = []
  const vibration = []
  const temperature = []
  const current = []
  const speed = []
  const acoustic = []
  const spectrumFreq = []
  const spectrumAmp = []

  for (let i = limit - 1; i >= 0; i--) {
    const t = new Date(now - i * 60000)
    const timeStr = `${t.getHours().toString().padStart(2, '0')}:${t.getMinutes().toString().padStart(2, '0')}`
    timestamps.push(timeStr)
    const base = deviceId.charCodeAt(5) % 5
    vibration.push(+(2 + base * 0.5 + Math.sin(i * 0.1) * 0.5 + Math.random() * 0.3).toFixed(3))
    temperature.push(+(65 + base * 3 + Math.sin(i * 0.08) * 2 + Math.random() * 1.5).toFixed(1))
    current.push(+(18 + base * 1.5 + Math.sin(i * 0.12) * 1 + Math.random() * 0.8).toFixed(2))
    speed.push(+(2980 + base * 20 + Math.sin(i * 0.05) * 15 + Math.random() * 10).toFixed(0))
    acoustic.push(+(75 + base * 4 + Math.sin(i * 0.07) * 3 + Math.random() * 2).toFixed(1))
  }

  for (let i = 0; i <= 200; i++) {
    spectrumFreq.push((i * 5).toFixed(0))
    const baseAmp = Math.sin(i * 0.05) * 0.3 + Math.sin(i * 0.1) * 0.2 + Math.sin(i * 0.3) * 0.15
    spectrumAmp.push(+(0.1 + Math.abs(baseAmp) + Math.random() * 0.1).toFixed(4))
  }

  return {
    timestamps,
    vibration,
    temperature,
    current,
    speed,
    acoustic,
    spectrum: {
      frequency: spectrumFreq,
      amplitude: spectrumAmp
    },
    latest: {
      vibration: vibration[vibration.length - 1],
      temperature: temperature[temperature.length - 1],
      current: current[current.length - 1],
      speed: speed[speed.length - 1],
      acoustic: acoustic[acoustic.length - 1],
      healthScore: +(85 - baseOffset(deviceId) + Math.random() * 10).toFixed(1),
      timestamp: timestamps[timestamps.length - 1]
    }
  }
}

const baseOffset = (deviceId) => {
  const map = { 'DEVV-001':00, DEVEV-202'88, DEVEV-303'3 3,DE'DEV4004'8 18DEV'DE5-005': 5 }
  return map[deviceId] || 0
}

const generateMockRULData = (deviceId) => {
  const now = Date.now()
  const history = []
  const forecast = []
  const baseHealth = 90 - baseOffset(deviceId)
  const baseRUL = 5000 - baseOffset(deviceId) * 400

  for (let i = 9; i >= 0; i--) {
    const t = new Date(now - i * 3600000 * 6)
    history.push({
      time: `${t.getMonth() + 1}/${t.getDate()} ${t.getHours().toString().padStart(2, '0')}:00`,
      health: +(baseHealth + i * 1.2 + Math.random() * 2).toFixed(1),
      rul: +(baseRUL + i * 80 + Math.random() * 50).toFixed(0)
    })
  }

  for (let i = 1; i <= 8; i++) {
    const t = new Date(now + i * 3600000 * 6)
    const h = +(baseHealth - i * 1.5 + Math.random() * 1).toFixed(1)
    const r = +(baseRUL - i * 100 + Math.random() * 30).toFixed(0)
    forecast.push({
      time: `${t.getMonth() + 1}/${t.getDate()} ${t.getHours().toString().padStart(2, '0')}:00`,
      health: h,
      rul: r,
      healthUpper: +(h + 3).toFixed(1),
      healthLower: +(h - 3).toFixed(1),
      rulUpper: r + 120,
      rulLower: r - 120
    })
  }

  return {
    currentRUL: baseRUL,
    currentHealth: baseHealth,
    warningThreshold: 60,
    criticalThreshold: 30,
    history,
    forecast
  }
}

const generateMockRootCause = (deviceId) => {
  const templates = {
    'AC-001': [
      { rank: 1, type: '排气阀片损坏', similarity: 92, confidence: 0.92, cause: '阀片长期高频冲击疲劳断裂，排气温度异常升高，排气量下降15-20%', solution: '建议在72小时内更换进排气阀组件（原厂件号VA-128），同时检查气阀弹簧' },
      { rank: 2, type: '活塞环磨损', similarity: 76, confidence: 0.76, cause: '活塞环磨损导致窜气，曲轴箱压力升高，润滑油消耗量增大', solution: '下次检修时检查活塞环开口间隙，超过0.8mm需成套更换' },
      { rank: 3, type: '润滑油超温', similarity: 58, confidence: 0.58, cause: '油冷却器结垢或温控阀故障，油温持续超过75℃加速油品氧化', solution: '清洗油冷却器芯子，校验温控阀开启温度（68±3℃），必要时更换润滑油' }
    ],
    'CP-001': [
      { rank: 1, type: '轴承磨损', similarity: 95, confidence: 0.95, cause: '滚动体与滚道长期疲劳接触导致表面剥落，振动频谱中出现2~5倍转频的特征频率', solution: '48小时内准备备用轴承（SKF 6312-2RS），72小时内停机更换' },
      { rank: 2, type: '叶轮堵塞', similarity: 68, confidence: 0.68, cause: '介质中含悬浮物沉积在叶轮流道，效率下降，流量减少约10%', solution: '解体清理叶轮，检查叶轮腐蚀情况，考虑加装入口过滤器' },
      { rank: 3, type: '机械密封泄漏', similarity: 54, confidence: 0.54, cause: '密封端面磨损，出现微量泄漏，介质侧温度异常', solution: '检查密封冲洗系统，准备备用密封组件（博格曼M7N/55）' }
    ],
    'FN-001': [
      { rank: 1, type: '叶轮积灰失衡', similarity: 88, confidence: 0.88, cause: '含尘气流长期运行，叶轮表面积灰不均造成质量不平衡，1倍转频振动显著增大', solution: '在线水洗清灰或停机人工清灰后做动平衡校正（G2.5级）' },
      { rank: 2, type: '皮带松动打滑', similarity: 72, confidence: 0.72, cause: 'V带磨损伸长，张力不足，转速下降约5-8%，电机电流波动', solution: '调整皮带张紧力或更换同型号三角带（5V-1600，4根成套）' },
      { rank: 3, type: '轴承润滑不足', similarity: 45, confidence: 0.45, cause: '轴承温度超过75℃，润滑脂流失或失效', solution: '补充高温润滑脂（壳牌爱比达HD2），检查轴承密封是否完好' }
    ],
    'CV-001': [
      { rank: 1, type: '托辊卡滞不转', similarity: 94, confidence: 0.94, cause: '托辊轴承进水进尘卡死不转，造成皮带异常磨损和运行阻力增大，电机电流升高', solution: '逐根检查卡滞托辊（目测或听音），更换密封型托辊组件（φ108×450）' },
      { rank: 2, type: '皮带跑偏', similarity: 81, confidence: 0.81, cause: '托辊组轴线不垂直皮带中心线，或滚筒安装不平行，皮带边缘磨损', solution: '调整头尾滚筒平行度，加装上调心托辊组，检查落料点对中' },
      { rank: 3, type: '减速器齿轮磨损', similarity: 62, confidence: 0.62, cause: '齿面出现点蚀和磨损，啮合噪声增大，油温偏高', solution: '取样化验齿轮油（L-CKD220），金属颗粒超标时安排检修齿轮副' }
    ],
    'CT-001': [
      { rank: 1, type: '风机轴承损坏', similarity: 85, confidence: 0.85, cause: '冷却风机轴承长期潮湿环境运行锈蚀，振动增大伴随异常噪声', solution: '停机更换风机轴承（NSK 6210-2RS），检查风机叶片腐蚀情况' },
      { rank: 2, type: '填料结垢堵塞', similarity: 65, confidence: 0.65, cause: '冷却水硬度高，填料表面结垢，冷却效率下降，出水温度升高3-5℃', solution: '停机化学清洗填料或更换PVC填料片，考虑加装旁流水处理' },
      { rank: 3, type: '布水器堵塞', similarity: 48, confidence: 0.48, cause: '布水器小孔被杂物堵塞，布水不均，部分填料未被水浸润', solution: '拆开布水器清理堵塞物，检查进水滤网是否破损' }
    ]
  }

  return {
    topCauses: templates[deviceId] || templates['AC-001'],
    suggestions: [
      '立即安排设备运维人员现场确认异常情况',
      '根据RUL预测结果，制定预防性维护计划窗口',
      '检查相关工艺参数是否在正常范围（压力/流量/负荷）',
      '对比同类型设备历史数据，确认故障发展趋势',
      '准备备品备件，评估停机风险与生产排程',
      '必要时启动应急预案，切换备用设备运行'
    ],
    overallConfidence: 0.87
  }
}

const generateMockAlerts = (deviceId) => {
  const alerts = [
    { id: 'A001', deviceId: 'AC-001', deviceName: '空压机', level: 'warning', time: '2026-06-15 14:23:45', message: '1级排气温度达到78℃，接近预警阈值80℃' },
    { id: 'A002', deviceId: 'CP-001', deviceName: '离心泵', level: 'severe', time: '2026-06-15 13:58:12', message: '驱动端轴承振动有效值达到6.8mm/s，超过ISO 10816-3报警限' },
    { id: 'A003', deviceId: 'CP-001', deviceName: '离心泵', level: 'severe', time: '2026-06-15 13:45:30', message: '机械密封泄漏监测点检测到介质泄漏，浓度0.8ppm' },
    { id: 'A004', deviceId: 'FN-001', deviceName: '风机', level: 'attention', time: '2026-06-15 12:30:20', message: '电机绕组温度较上周同期升高3.5℃' },
    { id: 'A005', deviceId: 'CV-001', deviceName: '传送带', level: 'warning', time: '2026-06-15 11:15:08', message: '电机电流达到11.5A，接近额定值12A' },
    { id: 'A006', deviceId: 'CT-001', deviceName: '冷却塔', level: 'attention', time: '2026-06-15 10:42:55', message: '循环水出水温度41℃，冷却效果略有下降' },
    { id: 'A007', deviceId: 'AC-001', deviceName: '空压机', level: 'attention', time: '2026-06-15 09:20:18', message: '润滑油压力较基准值变化0.08MPa，持续观察' },
    { id: 'A008', deviceId: 'FN-001', deviceName: '风机', level: 'warning', time: '2026-06-15 08:10:03', message: '风箱振动值达到4.2mm/s，接近报警阈值' }
  ]

  return deviceId ? alerts.filter(a => a.deviceId === deviceId) : alerts
}

export default request
