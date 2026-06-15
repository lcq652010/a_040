class WebSocketManager {
  constructor() {
    this.ws = null
    this.url = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 10
    this.reconnectDelay = 3000
    this.isManualClose = false
    this.heartbeatInterval = null
    this.messageHandlers = new Map()
    this.pendingRender = false
    this.renderQueue = []
    this.statusCallbacks = []
  }

  connect(url) {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this._notifyStatus('connected')
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
          this._notifyStatus('connected')
          this._startHeartbeat()
          resolve(this.ws)
        }

        this.ws.onmessage = (event) => {
          let data
          try {
            data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data
          } catch {
            data = event.data
          }
          this._handleMessage(data)
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket连接错误:', error)
          this._notifyStatus('error')
          reject(error)
        }

        this.ws.onclose = (event) => {
          this._stopHeartbeat()
          this._notifyStatus('disconnected')
          if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
            this._scheduleReconnect()
          }
        }
      } catch (error) {
        console.error('创建WebSocket实例失败:', error)
        reject(error)
      }
    })
  }

  _handleMessage(data) {
    if (data.type && data.type.startsWith('batch_')) {
      const originalType = data.type.replace('batch_', '')
      if (data.items && Array.isArray(data.items)) {
        for (const item of data.items) {
          this._enqueueRender(originalType, item)
        }
      }
    } else if (data.type) {
      this._enqueueRender(data.type, data.data)
    }
  }

  _enqueueRender(type, data) {
    this.renderQueue.push({ type, data })
    if (!this.pendingRender) {
      this.pendingRender = true
      requestAnimationFrame(() => this._flushRenderQueue())
    }
  }

  _flushRenderQueue() {
    const items = this.renderQueue.splice(0, this.renderQueue.length)
    this.pendingRender = false

    const merged = new Map()
    for (const item of items) {
      const key = `${item.type}:${item.data?.device_id || ''}`
      merged.set(key, item)
    }

    for (const item of merged.values()) {
      const handlers = this.messageHandlers.get(item.type) || []
      for (const handler of handlers) {
        try {
          handler(item.data)
        } catch (e) {
          console.error(`消息处理器错误 [${item.type}]:`, e)
        }
      }
    }
  }

  onMessage(type, callback) {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, [])
    }
    this.messageHandlers.get(type).push(callback)
    return () => {
      const handlers = this.messageHandlers.get(type)
      if (handlers) {
        const idx = handlers.indexOf(callback)
        if (idx > -1) handlers.splice(idx, 1)
      }
    }
  }

  offMessage(type, callback) {
    const handlers = this.messageHandlers.get(type)
    if (handlers) {
      const idx = handlers.indexOf(callback)
      if (idx > -1) handlers.splice(idx, 1)
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

  onStatusChange(callback) {
    if (typeof callback === 'function') {
      this.statusCallbacks.push(callback)
      return () => {
        const idx = this.statusCallbacks.indexOf(callback)
        if (idx > -1) this.statusCallbacks.splice(idx, 1)
      }
    }
  }

  _notifyStatus(status, info) {
    this.statusCallbacks.forEach(cb => {
      try { cb(status, info) } catch (e) { console.error('状态回调错误:', e) }
    })
  }

  getStatus() {
    if (!this.ws) return 'disconnected'
    const states = ['connecting', 'connected', 'closing', 'disconnected']
    return states[this.ws.readyState] || 'disconnected'
  }

  _scheduleReconnect() {
    this.reconnectAttempts++
    const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), 30000)
    this._notifyStatus('reconnecting', this.reconnectAttempts)

    setTimeout(() => {
      if (!this.isManualClose) {
        this.connect(this.url).catch(() => {})
      }
    }, delay)
  }

  _startHeartbeat() {
    this._stopHeartbeat()
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

  _stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  close() {
    this.isManualClose = true
    this._stopHeartbeat()
    if (this.ws) {
      this.ws.close(1000, 'Manual close')
      this.ws = null
    }
    this.messageHandlers.clear()
    this.renderQueue = []
    this.pendingRender = false
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
