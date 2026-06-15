<template>
  <div v-if="!rootCause" class="empty-state">
    <div class="empty-state-icon">🔍</div>
    <div class="empty-state-text">正在进行智能诊断分析...</div>
  </div>

  <div v-else>
    <div class="root-cause-list">
      <div
        v-for="cause in (rootCause.topCauses || [])"
        :key="cause.rank"
        class="root-cause-card"
      >
        <div class="root-cause-header">
          <div :class="['root-cause-rank', 'rank-' + cause.rank]">
            {{ cause.rank }}
          </div>
          <div class="root-cause-similarity">
            <div class="similarity-value">{{ cause.similarity }}%</div>
            <div class="similarity-label">相似度</div>
          </div>
        </div>

        <div class="root-cause-type">{{ cause.type }}</div>
        <div class="root-cause-detail">
          <strong>可能原因:</strong> {{ cause.cause }}
        </div>
        <div class="root-cause-detail">
          <strong>建议措施:</strong> {{ cause.solution }}
        </div>

        <div class="confidence-bar">
          <div
            class="confidence-fill"
            :style="{
              width: (cause.confidence * 100) + '%',
              background: getConfidenceGradient(cause.confidence)
            }"
          ></div>
        </div>
      </div>
    </div>

    <div v-if="rootCause.suggestions?.length" class="suggestion-list">
      <div class="suggestion-title">
        📋 综合处置建议
        <span :style="{
          marginLeft:'auto',
          fontSize:'11px',
          padding:'2px 8px',
          borderRadius:'10px',
          background:'rgba(24,144,255,0.15)',
          color:'var(--primary-light)',
          fontWeight:'normal'
        }">
          综合置信度: {{ Math.round((rootCause.overallConfidence || 0.85) * 100) }}%
        </span>
      </div>
      <ul class="suggestion-items">
        <li v-for="(s, i) in rootCause.suggestions" :key="i">{{ s }}</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
defineProps({
  rootCause: { type: Object, default: null }
})

const getConfidenceGradient = (conf) => {
  if (conf >= 0.85) {
    return 'linear-gradient(90deg, #73d13d, #52c41a)'
  }
  if (conf >= 0.7) {
    return 'linear-gradient(90deg, #ffc53d, #faad14)'
  }
  if (conf >= 0.5) {
    return 'linear-gradient(90deg, #ffa940, #fa8c16)'
  }
  return 'linear-gradient(90deg, #ff7875, #ff4d4f)'
}
</script>
