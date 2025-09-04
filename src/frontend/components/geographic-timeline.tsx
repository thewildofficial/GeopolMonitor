"use client"

import { useState, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { MapPin, Clock, TrendingUp, Globe } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { getFlagEmoji } from "@/lib/flags"

interface GeographicEvent {
  id: string
  location: string
  coordinates: [number, number]
  message: string
  timestamp: string
  urgency: number
  category: string
  channel: string
}

interface GeographicTimelineProps {
  messages: Array<{
    message_id: number
    channel_id: number
    text: string
    date: string
    channel_title: string
    urgency_score?: number
    detected_locations?: string[]
    categories?: string[]
  }>
}

// Mock coordinates for demo purposes
const LOCATION_COORDINATES: Record<string, [number, number]> = {
  "Middle East": [31.7683, 35.2137], // Jerusalem
  "Europe": [50.0755, 14.4378], // Prague
  "Asia": [35.6762, 139.6503], // Tokyo
  "United States": [39.8283, -98.5795], // Center of US
  "China": [39.9042, 116.4074], // Beijing
  "Russia": [55.7558, 37.6176], // Moscow
  "United Kingdom": [51.5074, -0.1278], // London
  "Germany": [52.5200, 13.4050], // Berlin
  "France": [48.8566, 2.3522], // Paris
  "Israel": [31.7683, 35.2137], // Jerusalem
  "Palestine": [31.9522, 35.2332], // Ramallah
  "South China Sea": [12.0000, 114.0000], // South China Sea
  "Philippines": [14.5995, 120.9842], // Manila
  "Syria": [33.5138, 36.2765], // Damascus
  "Yemen": [15.3694, 44.1910], // Sana'a
  "Afghanistan": [34.5553, 69.2075], // Kabul
  "Global": [0, 0], // Center of world map
  "European Union": [50.8503, 4.3517], // Brussels
}

export function GeographicTimeline({ messages }: GeographicTimelineProps) {
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState<"1h" | "6h" | "24h">("6h")

  // Convert messages to geographic events
  const geographicEvents: GeographicEvent[] = useMemo(() => {
    const events: GeographicEvent[] = []
    
    messages.forEach((message) => {
      if (message.detected_locations && message.detected_locations.length > 0) {
        message.detected_locations.forEach((location) => {
          const coordinates = LOCATION_COORDINATES[location] || [0, 0]
          events.push({
            id: `${message.message_id}-${location}`,
            location,
            coordinates,
            message: message.text,
            timestamp: message.date,
            urgency: message.urgency_score || 0,
            category: message.categories?.[0] || "general",
            channel: message.channel_title
          })
        })
      }
    })
    
    return events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  }, [messages])

  // Filter events by time range
  const filteredEvents = useMemo(() => {
    const now = new Date()
    const timeRangeMs = {
      "1h": 60 * 60 * 1000,
      "6h": 6 * 60 * 60 * 1000,
      "24h": 24 * 60 * 60 * 1000
    }[timeRange]

    return geographicEvents.filter(event => {
      const eventTime = new Date(event.timestamp)
      return now.getTime() - eventTime.getTime() <= timeRangeMs
    })
  }, [geographicEvents, timeRange])

  // Group events by location
  const eventsByLocation = useMemo(() => {
    const grouped: Record<string, GeographicEvent[]> = {}
    
    filteredEvents.forEach(event => {
      if (!grouped[event.location]) {
        grouped[event.location] = []
      }
      grouped[event.location].push(event)
    })
    
    return grouped
  }, [filteredEvents])

  // Get unique locations with event counts
  const locationStats = useMemo(() => {
    return Object.entries(eventsByLocation).map(([location, events]) => ({
      location,
      count: events.length,
      maxUrgency: Math.max(...events.map(e => e.urgency)),
      latestEvent: events[0], // Already sorted by timestamp
      coordinates: events[0].coordinates
    })).sort((a, b) => b.count - a.count)
  }, [eventsByLocation])

  const getUrgencyColor = (urgency: number) => {
    if (urgency >= 0.7) return "bg-red-600 text-white border-red-600"
    if (urgency >= 0.4) return "intel-badge-warning"
    return "intel-badge-success"
  }

  const getUrgencyLabel = (urgency: number) => {
    if (urgency >= 0.7) return "High"
    if (urgency >= 0.4) return "Medium"
    return "Low"
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <Card className="intel-card intel-glow">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Geographic Activity Timeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex gap-2">
              {(["1h", "6h", "24h"] as const).map((range) => (
                <Button
                  key={range}
                  variant={timeRange === range ? "default" : "outline"}
                  size="sm"
                  onClick={() => setTimeRange(range)}
                >
                  {range}
                </Button>
              ))}
            </div>
            <div className="text-sm text-muted-foreground">
              {filteredEvents.length} events across {locationStats.length} locations
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Location Overview */}
        <Card className="intel-card intel-glow">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" />
              Activity by Location
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px]">
              <div className="space-y-3">
                {locationStats.map((stat) => (
                  <div
                    key={stat.location}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedLocation === stat.location
                        ? "bg-intel-surface/70 border-intel-accent"
                        : "bg-intel-surface/40 border-intel-border hover:bg-intel-surface/60"
                    }`}
                    onClick={() => setSelectedLocation(
                      selectedLocation === stat.location ? null : stat.location
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-intel-accent" />
                        <span className="font-medium font-mono">
                          <span className="mr-1">{getFlagEmoji(stat.location)}</span>
                          {stat.location}
                        </span>
                        <Badge className="intel-badge-info">{stat.count}</Badge>
                      </div>
                      <Badge className={getUrgencyColor(stat.maxUrgency)}>
                        {getUrgencyLabel(stat.maxUrgency)}
                      </Badge>
                    </div>
                    <div className="text-sm text-intel-text-muted mt-1 font-mono">
                      Latest: {formatDistanceToNow(new Date(stat.latestEvent.timestamp), { addSuffix: true })}
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Timeline */}
        <Card className="intel-card intel-glow">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              {selectedLocation ? `${selectedLocation} Timeline` : "Recent Events"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px]">
              <div className="space-y-3">
                {(selectedLocation ? eventsByLocation[selectedLocation] || [] : filteredEvents.slice(0, 20)).map((event) => (
                  <div key={event.id} className="p-3 rounded-lg border border-intel-border bg-intel-surface/40">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <MapPin className="h-3 w-3 text-intel-accent" />
                          <span className="text-sm font-medium font-mono">
                            <span className="mr-1">{getFlagEmoji(event.location)}</span>
                            {event.location}
                          </span>
                          <Badge variant="outline" className="text-xs border-intel-border">
                            {event.category}
                          </Badge>
                          <Badge className={`text-xs ${getUrgencyColor(event.urgency)}`}>
                            {getUrgencyLabel(event.urgency)}
                          </Badge>
                        </div>
                        <p className="text-sm text-intel-text-secondary mb-2 line-clamp-2">
                          {event.message}
                        </p>
                        <div className="flex items-center gap-4 text-xs text-intel-text-muted font-mono">
                          <span className="truncate">{event.channel}</span>
                          <span>{formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Activity Heatmap Preview */}
      <Card className="intel-card intel-glow">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Activity Heatmap
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {locationStats.slice(0, 8).map((stat) => (
              <div key={stat.location} className="text-center">
                <div className="w-16 h-16 mx-auto rounded-full flex items-center justify-center text-white font-bold text-sm"
                     style={{
                       backgroundColor: `rgba(239, 68, 68, ${Math.min(stat.maxUrgency + 0.2, 1)})`,
                       fontSize: `${Math.max(10, 16 - stat.location.length)}px`
                     }}>
                  {stat.location.split(' ').map(word => word[0]).join('').slice(0, 2)}
                </div>
                <div className="mt-2 text-xs text-intel-text-muted font-mono">
                  <span className="mr-1">{getFlagEmoji(stat.location)}</span>
                  {stat.location}
                </div>
                <div className="text-xs font-medium">
                  {stat.count} events
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
