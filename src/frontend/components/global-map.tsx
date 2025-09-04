"use client"

import { useEffect, useRef, useState } from "react"
import maplibregl from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ZoomIn, ZoomOut, Maximize2, Layers } from "lucide-react"

export default function GlobalMap() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const [mapLoaded, setMapLoaded] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<any>(null)

  useEffect(() => {
    if (map.current || !mapContainer.current) return

    // Initialize map
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [0, 20],
      zoom: 2,
      pitch: 0,
    })

    map.current.on("load", () => {
      setMapLoaded(true)
      
      // Add navigation controls
      map.current?.addControl(new maplibregl.NavigationControl(), "top-right")
      
      // Add sample event markers
      const sampleEvents = [
        { lng: -74.006, lat: 40.7128, title: "New York", severity: "high" },
        { lng: -0.1276, lat: 51.5074, title: "London", severity: "medium" },
        { lng: 37.6173, lat: 55.7558, title: "Moscow", severity: "high" },
        { lng: 116.4074, lat: 39.9042, title: "Beijing", severity: "low" },
      ]

      sampleEvents.forEach((event) => {
        const el = document.createElement("div")
        el.className = "custom-marker"
        el.style.width = "20px"
        el.style.height = "20px"
        el.style.borderRadius = "50%"
        el.style.border = "2px solid white"
        el.style.cursor = "pointer"
        
        // Color based on severity
        if (event.severity === "high") {
          el.style.backgroundColor = "#ef4444"
        } else if (event.severity === "medium") {
          el.style.backgroundColor = "#f59e0b"
        } else {
          el.style.backgroundColor = "#10b981"
        }

        new maplibregl.Marker({ element: el })
          .setLngLat([event.lng, event.lat])
          .setPopup(
            new maplibregl.Popup({ offset: 25 }).setHTML(
              `<div class="p-2">
                <h3 class="font-bold">${event.title}</h3>
                <p class="text-sm">Severity: ${event.severity}</p>
              </div>`
            )
          )
          .addTo(map.current!)
      })
    })

    return () => {
      map.current?.remove()
      map.current = null
    }
  }, [])

  const handleZoomIn = () => {
    if (map.current) {
      map.current.zoomIn()
    }
  }

  const handleZoomOut = () => {
    if (map.current) {
      map.current.zoomOut()
    }
  }

  const handleFullscreen = () => {
    if (mapContainer.current) {
      if (!document.fullscreenElement) {
        mapContainer.current.requestFullscreen()
      } else {
        document.exitFullscreen()
      }
    }
  }

  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl">Global Intelligence Map</CardTitle>
              <CardDescription>Real-time geopolitical event visualization</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary">4 Active Events</Badge>
              <Badge variant="outline">Live</Badge>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Map Container */}
      <Card className="relative overflow-hidden">
        <CardContent className="p-0">
          <div ref={mapContainer} className="w-full h-[600px] relative">
            {!mapLoaded && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm">
                <div className="flex flex-col items-center gap-4">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                  <p className="text-muted-foreground">Loading map...</p>
                </div>
              </div>
            )}
            
            {/* Map Controls */}
            <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
              <Button size="icon" variant="secondary" onClick={handleZoomIn}>
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button size="icon" variant="secondary" onClick={handleZoomOut}>
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button size="icon" variant="secondary" onClick={handleFullscreen}>
                <Maximize2 className="h-4 w-4" />
              </Button>
              <Button size="icon" variant="secondary">
                <Layers className="h-4 w-4" />
              </Button>
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 left-4 z-10 bg-background/90 backdrop-blur-sm rounded-lg p-3 space-y-2">
              <p className="text-xs font-semibold mb-2">Event Severity</p>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <span className="text-xs">High</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="text-xs">Medium</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-xs">Low</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Event Details Panel */}
      {selectedEvent && (
        <Card>
          <CardHeader>
            <CardTitle>Event Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p className="text-sm">
                <span className="font-semibold">Location:</span> {selectedEvent.location}
              </p>
              <p className="text-sm">
                <span className="font-semibold">Time:</span> {selectedEvent.time}
              </p>
              <p className="text-sm">
                <span className="font-semibold">Description:</span> {selectedEvent.description}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}