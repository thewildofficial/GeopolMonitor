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
  media_urls?: string[]
  video_url?: string
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
    
    // Get WebSocket URL with proper fallback logic
    const getWebSocketUrl = () => {
      // First, try environment variable
      if (process.env.NEXT_PUBLIC_WS_URL) {
        return process.env.NEXT_PUBLIC_WS_URL
      }
      
      // In production, we should not fall back to localhost
      if (process.env.NODE_ENV === 'production') {
        console.error("❌ NEXT_PUBLIC_WS_URL environment variable is required in production")
        throw new Error("WebSocket URL not configured for production environment")
      }
      
      // Only use localhost in development
      if (process.env.NODE_ENV === 'development') {
        console.warn("⚠️ Using localhost fallback for WebSocket URL in development")
        return "http://localhost:8000"
      }
      
      // Fallback for other environments
      console.warn("⚠️ Using localhost fallback for WebSocket URL")
      return "http://localhost:8000"
    }
    
    const wsUrl = getWebSocketUrl()
    console.log(`🔗 Connecting to WebSocket at: ${wsUrl}`)
    
    // Connect to backend WebSocket server
    const socket = io(wsUrl, {
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
      setIsConnected(false)
    })

    socket.on("connect_error", (error) => {
      console.error("🚨 WebSocket connection error:", error)
      setIsConnected(false)
      
      // In production, provide more helpful error messages
      if (process.env.NODE_ENV === 'production') {
        console.error("❌ Failed to connect to WebSocket server. Please check your NEXT_PUBLIC_WS_URL configuration.")
      }
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