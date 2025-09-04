"use client"

import { useState, useEffect, useCallback } from "react"

interface TelegramMessage {
  message_id: number
  channel_id: number
  text: string
  date: string
  channel_title: string
  channel_username?: string
  urgency_score?: number
  relevance_score?: number
  sentiment_score?: number
  detected_locations?: string[]
  categories?: string[]
  time_sensitivity?: string
  views?: number
  forwards?: number
  has_media: boolean
  media_type?: string
}

interface TelegramChannel {
  channel_id: number
  username?: string
  title: string
  description?: string
  region?: string
  country?: string
  language: string
  category: string
  credibility_score: number
  priority_level: number
  is_active: boolean
  member_count?: number
}

interface TelegramStats {
  active_channels: number
  total_messages: number
  high_urgency_count: number
  messages_last_hour: number
  last_message_time?: string
}

interface ApiResponse<T> {
  data?: T
  error?: string
  loading: boolean
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function useTelegramMessages(filters?: {
  page?: number
  page_size?: number
  channel_id?: number
  urgency_min?: number
  relevance_min?: number
  location?: string
  time_sensitivity?: string
  start_date?: string
  end_date?: string
}) {
  const [response, setResponse] = useState<ApiResponse<{
    messages: TelegramMessage[]
    pagination: {
      page: number
      page_size: number
      total_count: number
      total_pages: number
      has_next: boolean
      has_prev: boolean
    }
  }>>({
    loading: true
  })

  const fetchMessages = useCallback(async () => {
    try {
      setResponse(prev => ({ ...prev, loading: true, error: undefined }))
      
      const params = new URLSearchParams()
      if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            params.append(key, value.toString())
          }
        })
      }
      
      const url = `${API_BASE_URL}/api/telegram/messages?${params.toString()}`
      const res = await fetch(url)
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }
      
      const data = await res.json()
      setResponse({ data, loading: false })
    } catch (error) {
      setResponse({
        error: error instanceof Error ? error.message : 'Unknown error',
        loading: false
      })
    }
  }, [filters])

  useEffect(() => {
    fetchMessages()
  }, [fetchMessages])

  return {
    ...response,
    refetch: fetchMessages
  }
}

export function useTelegramChannels() {
  const [response, setResponse] = useState<ApiResponse<{
    channels: TelegramChannel[]
  }>>({
    loading: true
  })

  const fetchChannels = useCallback(async () => {
    try {
      setResponse(prev => ({ ...prev, loading: true, error: undefined }))
      
      const url = `${API_BASE_URL}/api/telegram/channels`
      const res = await fetch(url)
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }
      
      const data = await res.json()
      setResponse({ data, loading: false })
    } catch (error) {
      setResponse({
        error: error instanceof Error ? error.message : 'Unknown error',
        loading: false
      })
    }
  }, [])

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels])

  return {
    ...response,
    refetch: fetchChannels
  }
}

export function useTelegramStats() {
  const [response, setResponse] = useState<ApiResponse<{
    stats: TelegramStats
    top_channels: Array<{
      title: string
      username?: string
      message_count: number
      avg_urgency?: number
    }>
    geographic_distribution: Array<{
      region: string
      message_count: number
    }>
  }>>({
    loading: true
  })

  const fetchStats = useCallback(async () => {
    try {
      setResponse(prev => ({ ...prev, loading: true, error: undefined }))
      
      const url = `${API_BASE_URL}/api/telegram/stats`
      const res = await fetch(url)
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }
      
      const data = await res.json()
      setResponse({ data, loading: false })
    } catch (error) {
      setResponse({
        error: error instanceof Error ? error.message : 'Unknown error',
        loading: false
      })
    }
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  return {
    ...response,
    refetch: fetchStats
  }
}
