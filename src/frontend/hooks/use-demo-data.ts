"use client"

import { useState, useEffect } from "react"

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

// Demo data for testing the frontend
const DEMO_MESSAGES: TelegramMessage[] = [
  {
    message_id: 1,
    channel_id: 1001,
    text: "BREAKING: Major diplomatic developments in the Middle East as new peace talks begin between regional powers. Sources indicate significant progress on key issues.",
    date: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    channel_title: "Global Affairs Monitor",
    channel_username: "globalaffairs",
    urgency_score: 0.9,
    relevance_score: 0.95,
    sentiment_score: 0.2,
    detected_locations: ["Middle East", "Israel", "Palestine"],
    categories: ["diplomacy", "peace", "breaking"],
    time_sensitivity: "breaking",
    views: 15420,
    forwards: 892,
    has_media: false
  },
  {
    message_id: 2,
    channel_id: 1002,
    text: "Economic indicators show mixed signals across European markets. While some sectors show resilience, others face continued pressure from geopolitical tensions.",
    date: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    channel_title: "European Economic Watch",
    channel_username: "euroecon",
    urgency_score: 0.4,
    relevance_score: 0.7,
    sentiment_score: -0.1,
    detected_locations: ["Europe", "Germany", "France"],
    categories: ["economics", "markets"],
    time_sensitivity: "normal",
    views: 3240,
    forwards: 156,
    has_media: true,
    media_type: "photo",
    media_urls: [
      "https://images.unsplash.com/photo-1520975916090-3105956dac38?q=80&w=1200&auto=format&fit=crop"
    ]
  },
  {
    message_id: 3,
    channel_id: 1003,
    text: "URGENT: Military exercises reported in disputed waters. Regional tensions escalate as multiple nations conduct simultaneous naval operations.",
    date: new Date(Date.now() - 18 * 60 * 1000).toISOString(),
    channel_title: "Asia Pacific Security",
    channel_username: "asiapacsec",
    urgency_score: 0.8,
    relevance_score: 0.85,
    sentiment_score: -0.3,
    detected_locations: ["South China Sea", "China", "Philippines"],
    categories: ["military", "security", "urgent"],
    time_sensitivity: "urgent",
    views: 8760,
    forwards: 423,
    has_media: true,
    media_type: "video",
    video_url: "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"
  },
  {
    message_id: 4,
    channel_id: 1004,
    text: "Climate summit concludes with new commitments from major economies. Renewable energy targets set for 2030, but critics question implementation timeline.",
    date: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
    channel_title: "Climate Policy Tracker",
    channel_username: "climatepolicy",
    urgency_score: 0.3,
    relevance_score: 0.6,
    sentiment_score: 0.1,
    detected_locations: ["Global", "United States", "European Union"],
    categories: ["climate", "policy", "energy"],
    time_sensitivity: "normal",
    views: 5420,
    forwards: 234,
    has_media: false
  },
  {
    message_id: 5,
    channel_id: 1005,
    text: "BREAKING: Cyber attack on critical infrastructure reported in multiple countries. Security agencies investigating potential state-sponsored activity.",
    date: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
    channel_title: "Cyber Security Alert",
    channel_username: "cybersecalert",
    urgency_score: 0.95,
    relevance_score: 0.9,
    sentiment_score: -0.4,
    detected_locations: ["United States", "United Kingdom", "Germany"],
    categories: ["cybersecurity", "infrastructure", "breaking"],
    time_sensitivity: "breaking",
    views: 12300,
    forwards: 567,
    has_media: true,
    media_type: "photo",
    media_urls: [
      "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?q=80&w=1200&auto=format&fit=crop",
      "https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?q=80&w=1200&auto=format&fit=crop"
    ]
  },
  {
    message_id: 6,
    channel_id: 1006,
    text: "Trade negotiations between major powers show signs of progress. New framework proposed for resolving longstanding disputes over technology transfers.",
    date: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
    channel_title: "Trade Relations Monitor",
    channel_username: "trademonitor",
    urgency_score: 0.5,
    relevance_score: 0.75,
    sentiment_score: 0.3,
    detected_locations: ["China", "United States", "European Union"],
    categories: ["trade", "technology", "diplomacy"],
    time_sensitivity: "normal",
    views: 6780,
    forwards: 189,
    has_media: false
  },
  {
    message_id: 7,
    channel_id: 1007,
    text: "Humanitarian crisis deepens in conflict zone. International aid organizations report increasing difficulty accessing affected populations.",
    date: new Date(Date.now() - 42 * 60 * 1000).toISOString(),
    channel_title: "Humanitarian Watch",
    channel_username: "humwatch",
    urgency_score: 0.7,
    relevance_score: 0.8,
    sentiment_score: -0.6,
    detected_locations: ["Syria", "Yemen", "Afghanistan"],
    categories: ["humanitarian", "crisis", "conflict"],
    time_sensitivity: "urgent",
    views: 9450,
    forwards: 312,
    has_media: true,
    media_type: "photo",
    media_urls: [
      "https://images.unsplash.com/photo-1517816743773-6e0fd518b4a6?q=80&w=1200&auto=format&fit=crop"
    ]
  },
  {
    message_id: 8,
    channel_id: 1008,
    text: "Space cooperation agreement signed between international partners. New satellite constellation planned for global communications and monitoring.",
    date: new Date(Date.now() - 50 * 60 * 1000).toISOString(),
    channel_title: "Space Policy Updates",
    channel_username: "spacepolicy",
    urgency_score: 0.2,
    relevance_score: 0.5,
    sentiment_score: 0.4,
    detected_locations: ["Global", "United States", "European Union"],
    categories: ["space", "technology", "cooperation"],
    time_sensitivity: "normal",
    views: 2890,
    forwards: 87,
    has_media: true,
    media_type: "diagram"
  }
]

const DEMO_CHANNELS = [
  {
    channel_id: 1001,
    username: "globalaffairs",
    title: "Global Affairs Monitor",
    description: "Comprehensive coverage of international diplomatic developments",
    region: "Global",
    country: "International",
    language: "en",
    category: "diplomacy",
    credibility_score: 9.2,
    priority_level: 9,
    is_active: true,
    member_count: 125000
  },
  {
    channel_id: 1002,
    username: "euroecon",
    title: "European Economic Watch",
    description: "Real-time economic analysis and market insights for Europe",
    region: "Europe",
    country: "European Union",
    language: "en",
    category: "economics",
    credibility_score: 8.7,
    priority_level: 8,
    is_active: true,
    member_count: 89000
  },
  {
    channel_id: 1003,
    username: "asiapacsec",
    title: "Asia Pacific Security",
    description: "Military and security developments in the Asia-Pacific region",
    region: "Asia",
    country: "Regional",
    language: "en",
    category: "security",
    credibility_score: 9.0,
    priority_level: 9,
    is_active: true,
    member_count: 156000
  },
  {
    channel_id: 1004,
    username: "climatepolicy",
    title: "Climate Policy Tracker",
    description: "Environmental policy and climate change developments",
    region: "Global",
    country: "International",
    language: "en",
    category: "environment",
    credibility_score: 8.5,
    priority_level: 7,
    is_active: true,
    member_count: 67000
  },
  {
    channel_id: 1005,
    username: "cybersecalert",
    title: "Cyber Security Alert",
    description: "Critical cybersecurity threats and infrastructure protection",
    region: "Global",
    country: "International",
    language: "en",
    category: "cybersecurity",
    credibility_score: 9.3,
    priority_level: 10,
    is_active: true,
    member_count: 198000
  }
]

export function useDemoTelegramData() {
  const [messages, setMessages] = useState<TelegramMessage[]>([])
  const [isConnected, setIsConnected] = useState(true)

  useEffect(() => {
    // Simulate real-time updates by adding new messages periodically
    setMessages(DEMO_MESSAGES)
    
    const interval = setInterval(() => {
      // Add a new random message every 30-60 seconds
      const newMessage: TelegramMessage = {
        message_id: Date.now(),
        channel_id: DEMO_CHANNELS[Math.floor(Math.random() * DEMO_CHANNELS.length)].channel_id,
        text: generateRandomMessage(),
        date: new Date().toISOString(),
        channel_title: DEMO_CHANNELS[Math.floor(Math.random() * DEMO_CHANNELS.length)].title,
        channel_username: DEMO_CHANNELS[Math.floor(Math.random() * DEMO_CHANNELS.length)].username,
        urgency_score: Math.random(),
        relevance_score: Math.random(),
        sentiment_score: (Math.random() - 0.5) * 2,
        detected_locations: ["Global", "United States", "Europe", "Asia"].slice(0, Math.floor(Math.random() * 3) + 1),
        categories: ["breaking", "urgent", "normal"][Math.floor(Math.random() * 3)],
        time_sensitivity: ["breaking", "urgent", "normal"][Math.floor(Math.random() * 3)],
        views: Math.floor(Math.random() * 20000),
        forwards: Math.floor(Math.random() * 1000),
        has_media: Math.random() > 0.5,
        media_type: ["photo", "video", "chart", "infographic"][Math.floor(Math.random() * 4)]
      }
      
      setMessages(prev => [newMessage, ...prev].slice(0, 100)) // Keep last 100 messages
    }, 30000 + Math.random() * 30000) // 30-60 seconds

    return () => clearInterval(interval)
  }, [])

  return {
    messages: messages.map(msg => ({ ...msg, type: "telegram_message" })),
    isConnected,
    channels: DEMO_CHANNELS,
    stats: {
      total_messages: messages.length,
      active_channels: DEMO_CHANNELS.length,
      high_urgency_count: messages.filter(m => (m.urgency_score || 0) >= 0.7).length,
      last_update: messages.length > 0 ? messages[0].date : new Date().toISOString()
    }
  }
}

function generateRandomMessage(): string {
  const templates = [
    "BREAKING: {event} reported in {location}. {details}",
    "URGENT: {event} escalates in {location}. {details}",
    "Update: {event} continues in {location}. {details}",
    "Analysis: {event} implications for {location}. {details}",
    "Report: {event} developments in {location}. {details}"
  ]
  
  const events = [
    "diplomatic tensions",
    "economic indicators",
    "security concerns",
    "trade negotiations",
    "climate developments",
    "cyber incidents",
    "military exercises",
    "humanitarian crisis"
  ]
  
  const locations = [
    "the Middle East",
    "Eastern Europe",
    "Southeast Asia",
    "the Arctic region",
    "the Mediterranean",
    "the Indo-Pacific",
    "Central America",
    "the Horn of Africa"
  ]
  
  const details = [
    "Sources indicate significant implications for regional stability.",
    "International observers are monitoring the situation closely.",
    "Multiple stakeholders are involved in ongoing discussions.",
    "The development follows weeks of escalating tensions.",
    "Experts warn of potential broader consequences.",
    "Local authorities are coordinating response efforts.",
    "The situation remains fluid with ongoing developments.",
    "International partners are being consulted on next steps."
  ]
  
  const template = templates[Math.floor(Math.random() * templates.length)]
  const event = events[Math.floor(Math.random() * events.length)]
  const location = locations[Math.floor(Math.random() * locations.length)]
  const detail = details[Math.floor(Math.random() * details.length)]
  
  return template
    .replace("{event}", event)
    .replace("{location}", location)
    .replace("{details}", detail)
}
