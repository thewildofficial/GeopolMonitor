"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"

// Sample data
const threatTrendData = [
  { date: "Mon", high: 4, medium: 10, low: 20 },
  { date: "Tue", high: 6, medium: 12, low: 18 },
  { date: "Wed", high: 8, medium: 15, low: 22 },
  { date: "Thu", high: 5, medium: 11, low: 25 },
  { date: "Fri", high: 7, medium: 13, low: 19 },
  { date: "Sat", high: 9, medium: 14, low: 21 },
  { date: "Sun", high: 6, medium: 16, low: 23 },
]

const sentimentData = [
  { name: "Positive", value: 30, color: "#10b981" },
  { name: "Neutral", value: 45, color: "#6b7280" },
  { name: "Negative", value: 25, color: "#ef4444" },
]

const channelActivityData = [
  { channel: "Reuters", messages: 120 },
  { channel: "BBC", messages: 95 },
  { channel: "CNN", messages: 80 },
  { channel: "AP News", messages: 70 },
  { channel: "Al Jazeera", messages: 65 },
]

const topEntities = [
  { entity: "United States", count: 245, trend: "up" },
  { entity: "China", count: 189, trend: "up" },
  { entity: "Russia", count: 156, trend: "down" },
  { entity: "NATO", count: 134, trend: "up" },
  { entity: "European Union", count: 128, trend: "stable" },
]

export default function AnalyticsDashboard() {
  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl">Analytics Dashboard</CardTitle>
              <CardDescription>Intelligence trends and insights</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary">Last 7 Days</Badge>
              <Badge variant="outline">Auto-refresh: ON</Badge>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total Messages</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,284</div>
            <p className="text-xs text-muted-foreground">+12% from last week</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">High Priority</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">42</div>
            <p className="text-xs text-muted-foreground">-8% from last week</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Active Channels</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">18</div>
            <p className="text-xs text-muted-foreground">+2 new this week</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Avg. Response Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3.2m</div>
            <p className="text-xs text-muted-foreground">-15% improvement</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <Tabs defaultValue="threats" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="threats">Threat Trends</TabsTrigger>
          <TabsTrigger value="sentiment">Sentiment Analysis</TabsTrigger>
          <TabsTrigger value="channels">Channel Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="threats" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Threat Level Trends</CardTitle>
              <CardDescription>Daily threat level distribution over the past week</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={threatTrendData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="date" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="high"
                    stroke="#ef4444"
                    strokeWidth={2}
                    name="High"
                  />
                  <Line
                    type="monotone"
                    dataKey="medium"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    name="Medium"
                  />
                  <Line
                    type="monotone"
                    dataKey="low"
                    stroke="#10b981"
                    strokeWidth={2}
                    name="Low"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sentiment" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Sentiment Distribution</CardTitle>
              <CardDescription>Overall sentiment analysis of intelligence feed</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={sentimentData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {sentimentData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="channels" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Channel Activity</CardTitle>
              <CardDescription>Message volume by intelligence channel</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={channelActivityData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis type="number" className="text-xs" />
                  <YAxis dataKey="channel" type="category" className="text-xs" />
                  <Tooltip />
                  <Bar dataKey="messages" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Top Entities */}
      <Card>
        <CardHeader>
          <CardTitle>Top Mentioned Entities</CardTitle>
          <CardDescription>Most frequently mentioned entities in the past 24 hours</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {topEntities.map((entity, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium">{index + 1}.</span>
                  <span className="text-sm">{entity.entity}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{entity.count}</Badge>
                  {entity.trend === "up" && (
                    <span className="text-xs text-green-500">↑</span>
                  )}
                  {entity.trend === "down" && (
                    <span className="text-xs text-red-500">↓</span>
                  )}
                  {entity.trend === "stable" && (
                    <span className="text-xs text-muted-foreground">→</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}