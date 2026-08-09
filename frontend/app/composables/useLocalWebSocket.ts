import { ref, onMounted, onUnmounted } from 'vue'

export function useLocalWebSocket(apiBaseUrl: string, onMessageCallback?: (data: any) => void) {
  const isConnected = ref(false)
  const lastEvent = ref<any>(null)
  let socket: WebSocket | null = null
  let reconnectTimer: any = null

  const connect = () => {
    try {
      // Convert http(s):// to ws(s)://
      const wsUrl = apiBaseUrl.replace(/^http/, 'ws') + '/ws'
      socket = new WebSocket(wsUrl)

      socket.onopen = () => {
        isConnected.value = true
        console.log('⚡ Connected to WashQueue Local Edge WebSocket.')
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          lastEvent.value = data
          if (onMessageCallback) {
            onMessageCallback(data)
          }
        } catch (e) {
          console.warn('Received non-JSON WebSocket message:', event.data)
        }
      }

      socket.onclose = () => {
        isConnected.value = false
        console.warn('WashQueue WebSocket disconnected. Reconnecting in 3s...')
        scheduleReconnect()
      }

      socket.onerror = (err) => {
        console.error('WashQueue WebSocket error:', err)
        if (socket) socket.close()
      }
    } catch (err) {
      console.error('Failed to initialize WebSocket connection:', err)
      scheduleReconnect()
    }
  }

  const scheduleReconnect = () => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(() => {
      connect()
    }, 3000)
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    if (socket) socket.close()
  })

  return {
    isConnected,
    lastEvent,
    reconnect: connect
  }
}
