"use client"

import * as React from "react"

type CarouselProps = React.HTMLAttributes<HTMLDivElement>

export function Carousel({ className = "", children, ...props }: CarouselProps) {
  return (
    <div className={`relative ${className}`} {...props}>
      {children}
    </div>
  )
}

type CarouselContentProps = React.HTMLAttributes<HTMLDivElement>

export const CarouselContent = React.forwardRef<HTMLDivElement, CarouselContentProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`flex w-full overflow-x-auto snap-x snap-mandatory gap-3 no-scrollbar scroll-smooth ${className}`}
        {...props}
      >
        {children}
      </div>
    )
  }
)
CarouselContent.displayName = "CarouselContent"

type CarouselItemProps = React.HTMLAttributes<HTMLDivElement>

export function CarouselItem({ className = "", children, ...props }: CarouselItemProps) {
  return (
    <div className={`snap-center shrink-0 w-full ${className}`} {...props}>
      {children}
    </div>
  )
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { targetRef?: React.RefObject<HTMLDivElement> }

export function CarouselPrevious({ className = "", targetRef, ...props }: ButtonProps) {
  const onClick = React.useCallback(() => {
    const el = targetRef?.current
    if (!el) return
    el.scrollBy({ left: -Math.max(300, el.clientWidth * 0.9), behavior: "smooth" })
  }, [targetRef])

  return (
    <button
      type="button"
      aria-label="Previous"
      onClick={onClick}
      className={`absolute left-2 top-1/2 -translate-y-1/2 z-10 h-8 w-8 rounded-md bg-black/40 hover:bg-black/60 text-white grid place-items-center border border-white/20 ${className}`}
      {...props}
    >
      ‹
    </button>
  )
}

export function CarouselNext({ className = "", targetRef, ...props }: ButtonProps) {
  const onClick = React.useCallback(() => {
    const el = targetRef?.current
    if (!el) return
    el.scrollBy({ left: Math.max(300, el.clientWidth * 0.9), behavior: "smooth" })
  }, [targetRef])

  return (
    <button
      type="button"
      aria-label="Next"
      onClick={onClick}
      className={`absolute right-2 top-1/2 -translate-y-1/2 z-10 h-8 w-8 rounded-md bg-black/40 hover:bg-black/60 text-white grid place-items-center border border-white/20 ${className}`}
      {...props}
    >
      ›
    </button>
  )
}

// utility: hide native scrollbar for a cleaner look
// Add the following to globals if not present:
// .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
// .no-scrollbar::-webkit-scrollbar { display: none; }



