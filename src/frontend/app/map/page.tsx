"use client"

import { GeographicTimeline } from "@/components/geographic-timeline"
import { useDemoTelegramData } from "@/hooks/use-demo-data"

export default function MapPage() {
  const { messages } = useDemoTelegramData()
  
  // Convert demo messages to the format expected by GeographicTimeline
  const formattedMessages = messages.map(msg => ({
    message_id: msg.message_id,
    channel_id: msg.channel_id,
    text: msg.text,
    date: msg.date,
    channel_title: msg.channel_title,
    urgency_score: msg.urgency_score,
    detected_locations: msg.detected_locations,
    categories: msg.categories
  }))

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Global Activity Map</h1>
        <p className="text-muted-foreground mt-1">
          Real-time geopolitical events mapped by location and time
        </p>
      </div>
      
      <GeographicTimeline messages={formattedMessages} />
    </div>
  )
}