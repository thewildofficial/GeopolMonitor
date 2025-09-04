"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import io, { Socket } from "socket.io-client"

interface Message {
  type: string
  message_id?: number
  channel_id?: number
  text?: string
  date?: string
  channel_title?: string
  channel_username?: string
  urgency_score?: number
  relevance_score?: number
  sentiment_score?: number
  detected_locations?: string[]
  categories?: string[]
  time_sensitivity?: string
  views?: number
  forwards?: number
  has_media?: boolean
  media_type?: string
  // Legacy fields for backward compatibility
  id?: string
  content?: string
  channel?: string
  timestamp?: string
  threatLevel?: string
  relevanceScore?: number
  sentiment?: {
    label: string
    score: number
  }
  location?: {
    country: string
    region?: string
  }
  entities?: string[]
  analysis?: any
}

export function useWebSocket() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const socketRef = useRef<Socket | null>(null)

  const connect = useCallback(() => {
    if (socketRef.current?.connected) return

    console.log("🔌 Attempting to connect to WebSocket...")
    
    // Connect to backend WebSocket server
    const socket = io(process.env.NEXT_PUBLIC_WS_URL || "http://localhost:8000", {
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    })

    socket.on("connect", () => {
      console.log("✅ WebSocket connected")
      setIsConnected(true)
    })

    socket.on("disconnect", () => {
      console.log("❌ WebSocket disconnected")
      setIsConnected(false)
    })

    socket.on("telegram_message", (message: Message) => {
      console.log("📨 New message received:", message)
      setMessages((prev) => [message, ...prev].slice(0, 100)) // Keep last 100 messages
    })

    // Also listen for general message updates
    socket.on("message", (message: Message) => {
      console.log("📨 New message received:", message)
      setMessages((prev) => [message, ...prev].slice(0, 100))
    })

    socket.on("error", (error) => {
      console.error("🚨 WebSocket error:", error)
    })

    socketRef.current = socket
  }, [])

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect()
      socketRef.current = null
    }
  }, [])

  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    messages,
    isConnected,
    connect,
    disconnect,
  }
}