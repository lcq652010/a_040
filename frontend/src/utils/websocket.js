class WebSocketManager {
  constructor() {
    this.ws = null
    this.url = null
    this.messageCallbacks = []
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 10
    this.reconnectDelay = 3000
    this.isManualClose = false
    this.heartbeatInterval = null
    this.statusCallbacks = []
  }

  connect(url) {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.notifyStatus('connected')
        resolve(this.ws)
        return
      }

      this.url = url
      this.isManualClose = false

      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = url.startsWith('ws') ? url : `${protocol}//${window.location.host}${url}`

        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          this.reconnectAttempts = 0
          this.notifyStatus('connected')
          this.startHeartbeat()
          resolve(this.ws)
        }

        this.ws.onmessage = (event) => {
          let data
          try {
            data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data
          } catch {
            data = event.data
          }
          this.messageCallbacks.forEach(cb => {
            try { cb(data) } catch (e) { console.error('消息回调错误:', e) }
          })
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket连接错误:', error)
          this.notifyStatus('error')
          reject(error)
        }

        this.ws.onclose = (event) => {
          this.stopHeartbeat()
          this.notifyStatus('disconnected')
          if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect()
          }
        }
      } catch (error) {
        console.error('创建WebSocket实例失败:', error)
        reject(error)
      }
    })
  }

  scheduleReconnect() {
    this.reconnectAttempts++
    const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), 30000)
    this.notifyStatus('reconnecting', this.reconnectAttempts)

    setTimeout(() => {
      if (!this.isManualClose) {
        this.connect(this.url).catch(() => {})
      }
    }, delay)
  }

  startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }))
        } catch (e) {
          console.error('心跳发送失败:', e)
        }
      }
    }, 30000)
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const msg = typeof data === 'string' ? data : JSON.stringify(data)
      this.ws.send(msg)
      return true
    }
    return false
  }

  onMessage(callback) {
    if (typeof callback === 'function') {
      this.messageCallbacks.push(callback)
      return () => {
        const idx = this.messageCallbacks.indexOf(callback)
        if (idx > -1) this.messageCallbacks.splice(idx, 1)
      }
    }
  }

  onStatusChange(callback) {
    if (typeof callback === 'function') {
      this.statusCallbacks.push(callback)
      return () => {
        const idx = this.statusCallbacks.indexOf(callback)
        if (idx > -1) this.statusCallbacks.splice(idx, 1)
      }
    }
  }

  notifyStatus(status, info) {
    this.statusCallbacks.forEach(cb => {
      try { cb(status, info) } catch (e) { console.error('状态回调错误:', e) }
    })
  }

  getStatus() {
    if (!this.ws) return 'disconnected'
    const states = ['connecting', 'connected', 'closing', 'disconnected']
    return states[this.ws.readyState] || 'disconnected'
  }

  close() {
    this.isManualClose = true
    this.stopHeartbeat()
    if (this.ws) {
      this.ws.close(1000, 'Manual close')
      this.ws = null
    }
    this.messageCallbacks = []
    this.reconnectAttempts = 0
  }

  reconnect() {
    this.close()
    this.isManualClose = false
    return this.connect(this.url)
  }
}

const wsManager = new WebSocketManager()

export default wsManager
