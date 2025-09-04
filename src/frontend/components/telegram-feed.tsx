"use client"

import { useState, useMemo, useEffect, useRef } from "react"
import { useWebSocket } from "@/hooks/use-websocket"
import { useDemoTelegramData } from "@/hooks/use-demo-data"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  MessageSquare,
  Users,
  Activity,
  AlertTriangle,
  Clock,
  Filter,
  Search,
  MapPin
} from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { FeedStats } from "./feed-stats"
import { MessageCard } from "./message-card"
import { FeedFilters } from "./feed-filters"

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
  media_urls?: string[]
  video_url?: string
}

export function TelegramFeed() {
  // Use demo data for now - switch to real WebSocket when backend is ready
  const { messages: demoMessages, isConnected: demoConnected, stats: demoStats } = useDemoTelegramData()
  const { messages: wsMessages, isConnected: wsConnected } = useWebSocket()
  
  // Use demo data if available, otherwise fall back to WebSocket
  const messages = demoMessages.length > 0 ? demoMessages : wsMessages
  const isConnected = demoMessages.length > 0 ? demoConnected : wsConnected
  
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedRegion, setSelectedRegion] = useState("all")
  const [selectedUrgency, setSelectedUrgency] = useState("all")
  const [selectedTimeframe, setSelectedTimeframe] = useState("1h")
  const [sortBy, setSortBy] = useState("date")

  // Convert messages to TelegramMessage format
  const telegramMessages: TelegramMessage[] = useMemo(() => {
    return messages
      .filter(msg => msg.type === "telegram_message")
      .map(msg => ({
        message_id: msg.message_id || Math.random(),
        channel_id: msg.channel_id || 0,
        text: msg.text || "",
        date: msg.date || new Date().toISOString(),
        channel_title: msg.channel_title || "Unknown Channel",
        channel_username: msg.channel_username,
        urgency_score: msg.urgency_score,
        relevance_score: msg.relevance_score,
        sentiment_score: msg.sentiment_score,
        detected_locations: msg.detected_locations || [],
        categories: msg.categories || [],
        time_sensitivity: msg.time_sensitivity,
        views: msg.views,
        forwards: msg.forwards,
        has_media: msg.has_media || false,
        media_type: msg.media_type,
        media_urls: (msg as any).media_urls || [],
        video_url: (msg as any).video_url
      }))
  }, [messages])

  // Filter and sort messages
  const filteredMessages = useMemo(() => {
    let filtered = telegramMessages

    // Search filter
    if (searchQuery) {
      filtered = filtered.filter(msg => 
        msg.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
        msg.channel_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        msg.detected_locations?.some(loc => 
          loc.toLowerCase().includes(searchQuery.toLowerCase())
        )
      )
    }

    // Region filter
    if (selectedRegion !== "all") {
      filtered = filtered.filter(msg => 
        msg.detected_locations?.some(loc => 
          loc.toLowerCase().includes(selectedRegion.toLowerCase())
        )
      )
    }

    // Urgency filter
    if (selectedUrgency !== "all") {
      filtered = filtered.filter(msg => {
        const urgency = msg.urgency_score || 0
        switch (selectedUrgency) {
          case "high": return urgency >= 0.7
          case "medium": return urgency >= 0.4 && urgency < 0.7
          case "low": return urgency < 0.4
          default: return true
        }
      })
    }

    // Timeframe filter
    const now = new Date()
    const timeframeMs = {
      "15m": 15 * 60 * 1000,
      "1h": 60 * 60 * 1000,
      "6h": 6 * 60 * 60 * 1000,
      "24h": 24 * 60 * 60 * 1000
    }[selectedTimeframe] || 60 * 60 * 1000

    filtered = filtered.filter(msg => {
      const msgDate = new Date(msg.date)
      return now.getTime() - msgDate.getTime() <= timeframeMs
    })

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case "urgency":
          return (b.urgency_score || 0) - (a.urgency_score || 0)
        case "relevance":
          return (b.relevance_score || 0) - (a.relevance_score || 0)
        case "engagement":
          return ((b.views || 0) + (b.forwards || 0)) - ((a.views || 0) + (a.forwards || 0))
        default:
          return new Date(b.date).getTime() - new Date(a.date).getTime()
      }
    })

    return filtered
  }, [telegramMessages, searchQuery, selectedRegion, selectedUrgency, selectedTimeframe, sortBy])

  // Calculate stats - use demo stats if available
  const stats = useMemo(() => {
    if (demoStats) {
      return demoStats
    }
    
    const highUrgencyCount = telegramMessages.filter(msg => (msg.urgency_score || 0) >= 0.7).length
    const uniqueChannels = new Set(telegramMessages.map(msg => msg.channel_id)).size
    const lastUpdate = telegramMessages.length > 0 ? telegramMessages[0].date : new Date().toISOString()

    return {
      total_messages: telegramMessages.length,
      active_channels: uniqueChannels,
      high_urgency_count: highUrgencyCount,
      last_update: lastUpdate
    }
  }, [telegramMessages, demoStats])

  // Integrate page scroll with feed scroll: when page reaches bottom and user keeps scrolling,
  // continue scrolling inside the feed ScrollArea instead of doing nothing.
  const feedContainerRef = useRef<HTMLDivElement | null>(null)
  const feedViewportRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!feedContainerRef.current) return
    // shadcn/radix adds an inner viewport element
    feedViewportRef.current = feedContainerRef.current.querySelector<HTMLElement>(
      '[data-radix-scroll-area-viewport]'
    ) as HTMLDivElement | null

    const onWheel = (e: WheelEvent) => {
      if (!feedViewportRef.current) return
      const atPageBottom =
        window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2
      if (!atPageBottom || e.deltaY <= 0) return

      const vp = feedViewportRef.current
      const maxScroll = vp.scrollHeight - vp.clientHeight
      if (maxScroll <= 0) return

      // If the feed can scroll further, consume the wheel event and scroll the feed
      if (vp.scrollTop < maxScroll) {
        e.preventDefault()
        vp.scrollTop = Math.min(maxScroll, vp.scrollTop + e.deltaY)
      }
    }

    // Use passive: false so we can preventDefault when needed
    window.addEventListener("wheel", onWheel, { passive: false })
    return () => window.removeEventListener("wheel", onWheel as EventListener)
  }, [])

  return (
    <div className="container mx-auto p-6 space-y-6 bg-intel-bg min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2 intel-matrix-text">
            <MessageSquare className="h-8 w-8 text-intel-accent" />
            <span className="font-mono">LIVE GEOPOLITICAL FEED</span>
          </h1>
          <p className="text-intel-text-secondary mt-1 font-mono text-sm">
            Real-time intelligence from {stats.active_channels} monitored sources
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`h-3 w-3 rounded-full ${isConnected ? 'bg-intel-success animate-intel-pulse' : 'bg-intel-danger'}`} />
          <span className="text-sm text-intel-text-secondary font-mono">
            {isConnected ? 'CONNECTED' : 'DISCONNECTED'}
          </span>
        </div>
      </div>

      {/* Stats Cards */}
      <FeedStats stats={stats} />

      {/* Filters */}
      <FeedFilters
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        selectedRegion={selectedRegion}
        setSelectedRegion={setSelectedRegion}
        selectedUrgency={selectedUrgency}
        setSelectedUrgency={setSelectedUrgency}
        selectedTimeframe={selectedTimeframe}
        setSelectedTimeframe={setSelectedTimeframe}
        sortBy={sortBy}
        setSortBy={setSortBy}
      />

      {/* Messages Feed */}
      <Card className="intel-card intel-glow">
        <CardHeader>
          <CardTitle className="intel-matrix-text">
            <span className="font-mono">LIVE INTELLIGENCE FEED ({filteredMessages.length} MESSAGES)</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea ref={feedContainerRef} className="h-[600px] intel-data-stream">
            <div className="space-y-4">
              {filteredMessages.length === 0 ? (
                <div className="text-center py-12 text-intel-text-muted">
                  <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50 text-intel-accent" />
                  <p className="font-mono">NO INTELLIGENCE DATA MATCHING FILTERS</p>
                  <p className="text-sm font-mono">ADJUST SEARCH CRITERIA OR TIMEFRAME</p>
                </div>
              ) : (
                filteredMessages.map((message) => (
                  <MessageCard key={`${message.channel_id}-${message.message_id}`} message={message} />
                ))
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}