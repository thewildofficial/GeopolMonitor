"use client"
import React from "react"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { MapPin } from "lucide-react"
import { getFlagEmoji } from "@/lib/flags"
import { formatDistanceToNow } from "date-fns"

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

interface MessageCardProps {
  message: TelegramMessage
}

export function MessageCard({ message }: MessageCardProps) {
  const getUrgencyColor = (score?: number) => {
    if (!score) return "intel-badge"
    // High urgency: solid red background with white text
    if (score >= 0.7) return "bg-red-600 text-white border-red-600 hover:bg-red-600"
    if (score >= 0.4) return "intel-badge-warning"
    return "intel-badge-success"
  }

  const getUrgencyLabel = (score?: number) => {
    if (!score) return "UNKNOWN"
    if (score >= 0.7) return "HIGH"
    if (score >= 0.4) return "MEDIUM"
    return "LOW"
  }

  const getSentimentColor = (score?: number) => {
    if (!score) return "text-intel-text-muted"
    if (score > 0.1) return "text-intel-success"
    if (score < -0.1) return "text-intel-danger"
    return "text-intel-text-muted"
  }

  const [isMediaExpanded, setIsMediaExpanded] = React.useState(false)

  return (
    <Card className="intel-card intel-glow hover:border-intel-accent transition-all duration-200">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-2">
            {/* Channel Info */}
            <div className="flex items-center gap-2">
              <Badge className="intel-badge text-xs font-mono">
                {message.channel_title}
              </Badge>
              {message.channel_username && (
                <span className="text-xs text-intel-text-muted font-mono">
                  @{message.channel_username}
                </span>
              )}
              <span className="text-xs text-intel-text-muted font-mono">
                {formatDistanceToNow(new Date(message.date), { addSuffix: true })}
              </span>
            </div>

            {/* Message Content */}
            <p className="text-sm leading-relaxed text-intel-text-primary">{message.text}</p>

            {/* Media (images/video) */}
            {message.has_media && (
              <div className="mt-2">
                {/* Video first if present */}
                {message.video_url ? (
                  <div
                    className={`group relative rounded-md overflow-hidden border border-intel-border bg-black/40 ${
                      isMediaExpanded ? "" : "max-h-48 cursor-zoom-in"
                    }`}
                    onClick={() => !isMediaExpanded && setIsMediaExpanded(true)}
                    role={!isMediaExpanded ? "button" : undefined}
                    aria-label={!isMediaExpanded ? "Expand video" : undefined}
                    tabIndex={!isMediaExpanded ? 0 : -1}
                    onKeyDown={(e) => {
                      if (!isMediaExpanded && (e.key === "Enter" || e.key === " ")) {
                        e.preventDefault()
                        setIsMediaExpanded(true)
                      }
                    }}
                  >
                    {!isMediaExpanded && (
                      <div className="absolute inset-0 bg-black/30 grid place-items-center text-xs font-mono text-white/90">
                        Click to expand
                      </div>
                    )}
                    <video
                      className={`w-full h-auto ${isMediaExpanded ? "" : "pointer-events-none"}`}
                      controls={isMediaExpanded}
                      preload="metadata"
                      src={message.video_url}
                    />
                  </div>
                ) : null}

                {/* Images carousel */}
                {Array.isArray(message.media_urls) && message.media_urls.length > 0 && (
                  <MediaCarousel
                    urls={message.media_urls}
                    collapsed={!isMediaExpanded}
                    onExpand={() => setIsMediaExpanded(true)}
                  />
                )}
              </div>
            )}

            {/* Metadata */}
            <div className="flex w-full flex-wrap items-center justify-between gap-3 sm:gap-4 text-xs leading-5 pt-3 mt-2 border-t border-intel-border/50">
              <div className="flex items-center flex-wrap gap-2 sm:gap-3 pr-2">
                {message.urgency_score !== undefined && (
                  <Badge className={`${getUrgencyColor(message.urgency_score)} text-xs font-mono`}>
                    {getUrgencyLabel(message.urgency_score)} URGENCY
                  </Badge>
                )}
                {message.sentiment_score !== undefined && (
                  <span className={`${getSentimentColor(message.sentiment_score)} font-mono`}>
                    SENTIMENT: {message.sentiment_score > 0 ? '+' : ''}{message.sentiment_score.toFixed(2)}
                  </span>
                )}
                {message.detected_locations && message.detected_locations.length > 0 && (
                  <div className="flex items-center gap-2">
                    <MapPin className="h-3 w-3 text-intel-accent" />
                    <div className="flex flex-wrap items-center gap-2">
                      {message.detected_locations.slice(0, 3).map((loc) => (
                        <span key={loc} className="text-intel-text-secondary font-mono inline-flex items-center gap-1">
                          <span className="text-sm leading-none">{getFlagEmoji(loc)}</span>
                          {loc}
                        </span>
                      ))}
                      {message.detected_locations.length > 3 && (
                        <span className="text-intel-text-muted font-mono">+{message.detected_locations.length - 3}</span>
                      )}
                    </div>
                  </div>
                )}
                {Array.isArray(message.categories) && message.categories.length > 0 && (
                  <div className="flex gap-1">
                    {message.categories.map((category) => (
                      <Badge key={String(category)} className="intel-badge text-xs font-mono">
                        {String(category).toUpperCase()}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2 sm:gap-3 pl-3 sm:pl-4 border-l border-intel-border/40">
                {message.has_media && (
                  <Badge className="intel-badge-info text-xs font-mono">
                    📎 {message.media_type || 'MEDIA'}
                  </Badge>
                )}
              </div>
            </div>

            {/* Engagement Metrics */}
            {(message.views || message.forwards) && (
              <div className="flex items-center gap-4 text-xs text-intel-text-muted font-mono">
                {message.views && (
                  <span>👁️ {message.views.toLocaleString()} VIEWS</span>
                )}
                {message.forwards && (
                  <span>↗️ {message.forwards.toLocaleString()} FORWARDS</span>
                )}
              </div>
            )}
          </div>

          {/* Urgency Indicator */}
          {message.urgency_score !== undefined && message.urgency_score >= 0.7 && (
            <div className="flex-shrink-0">
              <div className="h-3 w-3 bg-intel-danger rounded-full animate-intel-pulse" />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from "@/components/ui/carousel"
import { AspectRatio } from "@/components/ui/aspect-ratio"

function MediaCarousel({ urls, collapsed, onExpand }: { urls: string[]; collapsed: boolean; onExpand: () => void }) {
  const contentRef = React.useRef<HTMLDivElement>(null)
  return (
    <Carousel className={`relative ${collapsed ? "max-h-48 overflow-hidden cursor-zoom-in" : ""}`} onClick={() => collapsed && onExpand()}>
      <CarouselPrevious targetRef={contentRef} />
      <CarouselContent ref={contentRef} className="pb-1">
        {urls.map((url) => (
          <CarouselItem key={url} className="w-full">
            <div className="rounded-md overflow-hidden border border-intel-border bg-black/20">
              <AspectRatio ratio={16 / 9}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={url} alt="media" className="h-full w-full object-cover" loading="lazy" />
              </AspectRatio>
            </div>
          </CarouselItem>
        ))}
      </CarouselContent>
      <CarouselNext targetRef={contentRef} />
    </Carousel>
  )
}