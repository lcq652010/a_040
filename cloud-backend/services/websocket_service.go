package services

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"

	"phm-system/cloud-backend/models"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

type WebSocketClient struct {
	conn *websocket.Conn
	send chan []byte
}

type WebSocketHub struct {
	clients    map[*WebSocketClient]bool
	broadcast  chan []byte
	register   chan *WebSocketClient
	unregister chan *WebSocketClient
	mu         sync.RWMutex

	pendingMessages map[string][]interface{}
	flushTimer      *time.Timer
	flushChan       chan struct{}
}

func NewWebSocketHub() *WebSocketHub {
	return &WebSocketHub{
		clients:         make(map[*WebSocketClient]bool),
		broadcast:       make(chan []byte, 256),
		register:        make(chan *WebSocketClient),
		unregister:      make(chan *WebSocketClient),
		pendingMessages: make(map[string][]interface{}),
		flushChan:       make(chan struct{}, 1),
	}
}

func (hub *WebSocketHub) Run() {
	for {
		select {
		case client := <-hub.register:
			hub.mu.Lock()
			hub.clients[client] = true
			hub.mu.Unlock()
			log.Printf("WebSocket client connected, total: %d", len(hub.clients))

		case client := <-hub.unregister:
			hub.mu.Lock()
			if _, ok := hub.clients[client]; ok {
				delete(hub.clients, client)
				close(client.send)
			}
			hub.mu.Unlock()
			log.Printf("WebSocket client disconnected, total: %d", len(hub.clients))

		case message := <-hub.broadcast:
			hub.mu.RLock()
			for client := range hub.clients {
				select {
				case client.send <- message:
				default:
					hub.mu.RUnlock()
					hub.mu.Lock()
					close(client.send)
					delete(hub.clients, client)
					hub.mu.Unlock()
					hub.mu.RLock()
				}
			}
			hub.mu.RUnlock()

		case <-hub.flushChan:
			hub.flushPendingMessages()
		}
	}
}

func (hub *WebSocketHub) HandleWebSocket(c *gin.Context) {
	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}

	client := &WebSocketClient{
		conn: conn,
		send: make(chan []byte, 256),
	}

	hub.register <- client

	defer func() {
		hub.unregister <- client
	}()

	go client.writePump()
	client.readPump(hub)
}

func (client *WebSocketClient) readPump(hub *WebSocketHub) {
	defer func() {
		hub.unregister <- client
		client.conn.Close()
	}()

	client.conn.SetReadLimit(512 * 1024)
	_ = client.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	client.conn.SetPongHandler(func(string) error {
		_ = client.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})

	for {
		_, _, err := client.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket read error: %v", err)
			}
			break
		}
	}
}

func (client *WebSocketClient) writePump() {
	ticker := time.NewTicker(54 * time.Second)
	defer func() {
		ticker.Stop()
		client.conn.Close()
	}()

	for {
		select {
		case message, ok := <-client.send:
			_ = client.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if !ok {
				_ = client.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			if err := client.conn.WriteMessage(websocket.TextMessage, message); err != nil {
				log.Printf("WebSocket write error: %v", err)
				return
			}

		case <-ticker.C:
			_ = client.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := client.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

func (hub *WebSocketHub) Broadcast(message *models.WebSocketMessage) {
	hub.mu.Lock()
	hub.pendingMessages[message.Type] = append(hub.pendingMessages[message.Type], message.Data)

	if hub.flushTimer == nil {
		hub.flushTimer = time.AfterFunc(50*time.Millisecond, func() {
			select {
			case hub.flushChan <- struct{}{}:
			default:
			}
		})
	}
	hub.mu.Unlock()
}

func (hub *WebSocketHub) flushPendingMessages() {
	hub.mu.Lock()

	if len(hub.pendingMessages) == 0 {
		hub.mu.Unlock()
		return
	}

	pending := hub.pendingMessages
	hub.pendingMessages = make(map[string][]interface{})

	if hub.flushTimer != nil {
		hub.flushTimer.Stop()
		hub.flushTimer = nil
	}

	hub.mu.Unlock()

	for msgType, items := range pending {
		var jsonData []byte
		var err error

		if len(items) == 1 {
			msg := &models.WebSocketMessage{
				Type:      msgType,
				Data:      items[0],
				Timestamp: time.Now(),
			}
			jsonData, err = json.Marshal(msg)
		} else {
			itemMaps := make([]map[string]interface{}, 0, len(items))
			for _, item := range items {
				b, mErr := json.Marshal(item)
				if mErr != nil {
					log.Printf("Failed to marshal pending item: %v", mErr)
					continue
				}
				var m map[string]interface{}
				if umErr := json.Unmarshal(b, &m); umErr != nil {
					log.Printf("Failed to unmarshal pending item: %v", umErr)
					continue
				}
				itemMaps = append(itemMaps, m)
			}
			batch := &models.BatchWebSocketMessage{
				Type:      "batch_" + msgType,
				Items:     itemMaps,
				Count:     len(itemMaps),
				Timestamp: time.Now(),
			}
			jsonData, err = json.Marshal(batch)
		}

		if err != nil {
			log.Printf("Failed to marshal flush message: %v", err)
			continue
		}

		hub.broadcast <- jsonData
	}
}

func (hub *WebSocketHub) BroadcastDeviceUpdate(data *models.DeviceData) {
	msg := &models.WebSocketMessage{
		Type:      "device_update",
		Data:      data,
		Timestamp: time.Now(),
	}
	hub.Broadcast(msg)
}

func (hub *WebSocketHub) BroadcastRULUpdate(prediction *models.RULPrediction) {
	msg := &models.WebSocketMessage{
		Type:      "rul_update",
		Data:      prediction,
		Timestamp: time.Now(),
	}
	hub.Broadcast(msg)
}

func (hub *WebSocketHub) BroadcastAlert(alert *models.AlertMessage) {
	msg := &models.WebSocketMessage{
		Type:      "alert",
		Data:      alert,
		Timestamp: time.Now(),
	}
	hub.Broadcast(msg)
}

func (hub *WebSocketHub) BroadcastRootCause(result *models.RootCauseResult) {
	msg := &models.WebSocketMessage{
		Type:      "root_cause_result",
		Data:      result,
		Timestamp: time.Now(),
	}
	hub.Broadcast(msg)
}
