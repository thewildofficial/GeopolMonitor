"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Filter, Search } from "lucide-react"

interface FeedFiltersProps {
  searchQuery: string
  setSearchQuery: (query: string) => void
  selectedRegion: string
  setSelectedRegion: (region: string) => void
  selectedUrgency: string
  setSelectedUrgency: (urgency: string) => void
  selectedTimeframe: string
  setSelectedTimeframe: (timeframe: string) => void
  sortBy: string
  setSortBy: (sort: string) => void
}

export function FeedFilters({
  searchQuery,
  setSearchQuery,
  selectedRegion,
  setSelectedRegion,
  selectedUrgency,
  setSelectedUrgency,
  selectedTimeframe,
  setSelectedTimeframe,
  sortBy,
  setSortBy
}: FeedFiltersProps) {
  return (
    <Card className="intel-card intel-glow">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 intel-matrix-text">
          <Filter className="h-5 w-5 text-intel-accent" />
          <span className="font-mono">FILTERS & CONTROLS</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          <div className="md:col-span-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-intel-text-muted" />
              <Input
                placeholder="Search intelligence data..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 intel-input font-mono"
              />
            </div>
          </div>
          <Select value={selectedRegion} onValueChange={setSelectedRegion}>
            <SelectTrigger>
              <SelectValue placeholder="Region" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Regions</SelectItem>
              <SelectItem value="europe">Europe</SelectItem>
              <SelectItem value="asia">Asia</SelectItem>
              <SelectItem value="americas">Americas</SelectItem>
              <SelectItem value="africa">Africa</SelectItem>
              <SelectItem value="middle east">Middle East</SelectItem>
            </SelectContent>
          </Select>
          <Select value={selectedUrgency} onValueChange={setSelectedUrgency}>
            <SelectTrigger>
              <SelectValue placeholder="Urgency" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Urgency</SelectItem>
              <SelectItem value="high">High Urgency</SelectItem>
              <SelectItem value="medium">Medium Urgency</SelectItem>
              <SelectItem value="low">Low Urgency</SelectItem>
            </SelectContent>
          </Select>
          <Select value={selectedTimeframe} onValueChange={setSelectedTimeframe}>
            <SelectTrigger>
              <SelectValue placeholder="Timeframe" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="15m">Last 15 minutes</SelectItem>
              <SelectItem value="1h">Last hour</SelectItem>
              <SelectItem value="6h">Last 6 hours</SelectItem>
              <SelectItem value="24h">Last 24 hours</SelectItem>
            </SelectContent>
          </Select>
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger>
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date">Most Recent</SelectItem>
              <SelectItem value="urgency">Highest Urgency</SelectItem>
              <SelectItem value="relevance">Most Relevant</SelectItem>
              <SelectItem value="engagement">Most Engaged</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  )
}
