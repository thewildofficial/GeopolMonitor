"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu"
import { Button } from "@/components/ui/button"
import { Home, MessageSquare, Globe, BarChart3 } from "lucide-react"

const navItems = [
  {
    name: "Dashboard",
    href: "/dashboard",
    icon: Home,
  },
  {
    name: "Telegram Feed",
    href: "/telegram",
    icon: MessageSquare,
  },
  {
    name: "Global Map",
    href: "/map",
    icon: Globe,
  },
  {
    name: "Analytics",
    href: "/analytics",
    icon: BarChart3,
  },
]

export function Navigation() {
  const pathname = usePathname()

  const isActive = (href: string) => {
    if (href === "/") {
      return pathname === "/"
    }
    return pathname.startsWith(href)
  }

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-intel-border bg-intel-surface/95 backdrop-blur supports-[backdrop-filter]:bg-intel-surface/60 intel-scan">
      <div className="container flex h-16 items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2 font-bold text-xl mr-6 intel-glow">
          <span className="text-2xl intel-matrix-text">🛰️</span>
          <span className="hidden sm:inline intel-matrix-text font-mono">GeopolMonitor</span>
        </Link>

        {/* Navigation Menu */}
        <NavigationMenu className="flex-1 flex justify-center">
          <NavigationMenuList>
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <NavigationMenuItem key={item.href}>
                  <NavigationMenuLink asChild>
                    <Link 
                      href={item.href}
                      className={cn(
                        navigationMenuTriggerStyle(),
                        isActive(item.href) && "bg-accent text-accent-foreground"
                      )}
                    >
                      <Icon className="h-4 w-4 mr-2" />
                      <span className="hidden sm:inline">{item.name}</span>
                    </Link>
                  </NavigationMenuLink>
                </NavigationMenuItem>
              )
            })}
          </NavigationMenuList>
        </NavigationMenu>

        {/* Actions */}
        <div className="flex items-center gap-4 ml-auto">
          {/* Live Status Indicator */}
          <div className="flex items-center gap-2 px-3 py-1 bg-intel-success/10 border border-intel-success/30 rounded-full intel-glow">
            <div className="h-2 w-2 bg-intel-success rounded-full animate-intel-pulse" />
            <span className="text-xs font-semibold text-intel-success font-mono">LIVE</span>
          </div>
        </div>
      </div>
    </nav>
  )
}