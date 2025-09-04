"use client"

import { useState, useCallback } from "react"

interface Filters {
  threatLevel?: string
  channel?: string
  searchTerm?: string
  dateRange?: {
    start: Date
    end: Date
  }
}

interface Message {
  id: string
  content: string
  channel: string
  timestamp: string
  threatLevel?: string
  [key: string]: any
}

export function useFilters() {
  const [filters, setFilters] = useState<Filters>({})

  const updateFilter = useCallback((key: keyof Filters, value: any) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
    }))
  }, [])

  const clearFilters = useCallback(() => {
    setFilters({})
  }, [])

  const applyFilters = useCallback((messages: Message[]): Message[] => {
    return messages.filter((message) => {
      // Filter by threat level
      if (filters.threatLevel && message.threatLevel !== filters.threatLevel) {
        return false
      }

      // Filter by channel
      if (filters.channel && message.channel !== filters.channel) {
        return false
      }

      // Filter by search term
      if (filters.searchTerm && 
          !message.content.toLowerCase().includes(filters.searchTerm.toLowerCase())) {
        return false
      }

      // Filter by date range
      if (filters.dateRange) {
        const messageDate = new Date(message.timestamp)
        if (messageDate < filters.dateRange.start || messageDate > filters.dateRange.end) {
          return false
        }
      }

      return true
    })
  }, [filters])

  return {
    filters,
    updateFilter,
    clearFilters,
    applyFilters,
  }
}