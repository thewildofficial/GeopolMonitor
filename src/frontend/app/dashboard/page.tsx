"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  Activity, 
  AlertTriangle, 
  Globe, 
  MessageSquare, 
  TrendingUp,
  Users,
  Clock,
  MapPin
} from "lucide-react"
import { useDemoTelegramData } from "@/hooks/use-demo-data"
import { GeographicTimeline } from "@/components/geographic-timeline"
import { MessageCard } from "@/components/message-card"
import { formatDistanceToNow } from "date-fns"
import { getFlagEmoji } from "@/lib/flags"

export default function DashboardPage() {
  const { messages, stats, channels } = useDemoTelegramData()
  const [selectedTab, setSelectedTab] = useState("overview")

  // Get high urgency messages
  const highUrgencyMessages = messages
    .filter(msg => (msg.urgency_score || 0) >= 0.7)
    .slice(0, 5)

  // Get recent messages
  const recentMessages = messages.slice(0, 10)

  // Format messages for geographic timeline
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

  // Calculate activity metrics
  const activityMetrics = {
    messagesLastHour: messages.filter(msg => {
      const msgTime = new Date(msg.date)
      const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000)
      return msgTime > oneHourAgo
    }).length,
    topRegions: Object.entries(
      messages.reduce((acc, msg) => {
        msg.detected_locations?.forEach(location => {
          acc[location] = (acc[location] || 0) + 1
        })
        return acc
      }, {} as Record<string, number>)
    ).sort(([,a], [,b]) => b - a).slice(0, 5),
    channelActivity: channels.map(channel => ({
      ...channel,
      messageCount: messages.filter(msg => msg.channel_id === channel.channel_id).length
    })).sort((a, b) => b.messageCount - a.messageCount).slice(0, 5)
  }

  return (
    <div className="container mx-auto p-6 space-y-6 bg-intel-bg min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold intel-matrix-text">
            <span className="font-mono">GEOPOLITICAL INTELLIGENCE DASHBOARD</span>
          </h1>
          <p className="text-intel-text-secondary mt-1 font-mono text-sm">
            Real-time open-source intelligence (OSINT) from {stats.active_channels} monitored sources
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 bg-intel-success rounded-full animate-intel-pulse" />
          <span className="text-sm text-intel-text-secondary font-mono">LIVE</span>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="intel-card intel-glow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-intel-info" />
              <div>
                <p className="text-sm text-intel-text-secondary font-mono">TOTAL MESSAGES</p>
                <p className="text-2xl font-bold text-intel-text-primary font-mono">{stats.total_messages}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="intel-card intel-glow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-intel-success" />
              <div>
                <p className="text-sm text-intel-text-secondary font-mono">ACTIVE CHANNELS</p>
                <p className="text-2xl font-bold text-intel-text-primary font-mono">{stats.active_channels}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="intel-card intel-glow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-intel-danger" />
              <div>
                <p className="text-sm text-intel-text-secondary font-mono">HIGH URGENCY</p>
                <p className="text-2xl font-bold text-intel-text-primary font-mono">{stats.high_urgency_count}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="intel-card intel-glow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-intel-warning" />
              <div>
                <p className="text-sm text-intel-text-secondary font-mono">LAST HOUR</p>
                <p className="text-2xl font-bold text-intel-text-primary font-mono">{activityMetrics.messagesLastHour}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="alerts">High Priority</TabsTrigger>
          <TabsTrigger value="geographic">Geographic</TabsTrigger>
          <TabsTrigger value="channels">Channels</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Recent Activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recentMessages.slice(0, 5).map((message) => (
                    <div key={message.message_id} className="p-4 rounded-lg intel-card intel-glow">
                      {/* Header row: channel left, urgency right */}
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs font-mono">
                            {message.channel_title}
                          </Badge>
                        </div>
                        {message.urgency_score && message.urgency_score >= 0.7 && (
                          <Badge className="text-xs font-mono bg-red-600 text-white border-red-600 hover:bg-red-600">
                            HIGH URGENCY
                          </Badge>
                        )}
                      </div>

                      {/* Message text */}
                      <p className="text-sm text-intel-text-primary leading-relaxed line-clamp-2">
                        {message.text}
                      </p>

                      {/* Meta row: locations left, time right */}
                      <div className="flex items-center justify-between mt-2 text-xs text-intel-text-muted">
                        {message.detected_locations && message.detected_locations.length > 0 ? (
                          <div className="flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            <span className="font-mono">
                              {message.detected_locations.join(', ')}
                            </span>
                          </div>
                        ) : <span />}
                        <span className="font-mono">
                          {formatDistanceToNow(new Date(message.date), { addSuffix: true })}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Top Regions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Globe className="h-5 w-5" />
                  Activity by Region
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {activityMetrics.topRegions.map(([region, count]) => (
                    <div key={region} className="flex items-center justify-between p-3 rounded-lg border">
                      <div className="flex items-center gap-2">
                        <span className="text-lg leading-none">{getFlagEmoji(region)}</span>
                        <span className="font-medium">{region}</span>
                      </div>
                      <Badge variant="secondary">{count} events</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="alerts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-600" />
                High Priority Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {highUrgencyMessages.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No high priority alerts at this time</p>
                  </div>
                ) : (
                  highUrgencyMessages.map((message) => (
                    <MessageCard key={message.message_id} message={message} />
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="geographic" className="space-y-4">
          <GeographicTimeline messages={formattedMessages} />
        </TabsContent>

        <TabsContent value="channels" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Channel Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {activityMetrics.channelActivity.map((channel) => (
                  <div key={channel.channel_id} className="flex items-center justify-between p-3 rounded-lg border">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                        <span className="text-blue-600 font-bold text-sm">
                          {channel.title.charAt(0)}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium">{channel.title}</p>
                        <p className="text-sm text-muted-foreground">
                          {channel.region} • {channel.member_count?.toLocaleString()} members
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge variant="secondary">{channel.messageCount} messages</Badge>
                      <div className="text-xs text-muted-foreground mt-1">
                        Credibility: {channel.credibility_score}/10
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
