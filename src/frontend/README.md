# GeopolMonitor SvelteKit Frontend

Modern SvelteKit-based frontend for the GeopolMonitor intelligence platform, replacing the previous HTML/CSS/JS implementation with a reactive, component-based architecture.

## 🚀 Features

- **Reactive State Management**: Uses Svelte stores for real-time data handling
- **TypeScript**: Full type safety for complex geopolitical data structures
- **WebSocket Integration**: Live connection to Flask backend with auto-reconnection
- **Professional OSINT UI**: Dark theme intelligence dashboard design
- **Performance Optimized**: Virtual scrolling, efficient updates, small bundles
- **Mobile Responsive**: Touch-optimized for field operations

## 📁 Project Structure

```
src/
├── lib/
│   ├── components/          # Svelte components
│   │   ├── TelegramFeed.svelte     # Main feed component
│   │   └── MessageCard.svelte      # Individual message cards
│   ├── stores/             # Reactive state management
│   │   ├── websocket.ts           # WebSocket connection
│   │   └── filters.ts             # Message filtering
│   ├── types/              # TypeScript interfaces
│   │   └── index.ts               # Core data types
│   └── styles/             # Global styles
│       └── global.css             # OSINT design system
├── routes/                 # SvelteKit pages
│   ├── +layout.svelte             # App layout
│   └── telegram/                  # Telegram intelligence feed
│       └── +page.svelte
└── app.html               # HTML template
```

## 🛠️ Development

### Prerequisites

- Node.js 18+ 
- npm or pnpm

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Development Server

The dev server runs on `http://localhost:5173` and proxies API calls to the Flask backend at `http://localhost:8000`.

## 🔧 Integration with Flask Backend

This SvelteKit app is designed to integrate seamlessly with the existing Flask backend:

- **Static Build**: Outputs to `../web/static/svelte-build/` for Flask serving
- **API Proxy**: Development server proxies `/api` and `/ws` to Flask
- **WebSocket**: Connects to Flask WebSocket endpoint for real-time data

## 🎨 Design System

The app uses a professional OSINT (Open Source Intelligence) design system:

- **Colors**: Deep navy backgrounds with cyan accents
- **Typography**: Inter font family for clarity
- **Shadows**: Subtle depth for professional appearance
- **Components**: Reusable card, button, and form components

## 📱 Components

### TelegramFeed
Main component displaying the live intelligence feed with:
- Real-time message stream
- Connection status indicator
- Statistics display
- Auto-scroll functionality

### MessageCard
Individual message display with:
- Threat level indicators
- Relevance scoring
- Sentiment analysis
- Geographic information
- Action buttons (analyze, bookmark, share)

## 🔄 State Management

### WebSocket Store (`websocket.ts`)
- Connection state management
- Auto-reconnection logic
- Message buffering
- Latency monitoring

### Filter Store (`filters.ts`)
- Real-time message filtering
- Search functionality
- Statistics derivation
- Filter persistence

## 🚀 Deployment

The build process creates static assets that can be served by Flask:

```bash
npm run build
```

This outputs optimized files to `../web/static/svelte-build/` which Flask can serve directly.

## 🔒 Security

- TypeScript provides compile-time type checking
- Input validation on all WebSocket messages
- XSS protection through Svelte's automatic escaping
- CSP-friendly design without inline scripts

## 📊 Performance

- **Bundle Size**: Optimized for fast loading (< 100KB gzipped)
- **Virtual Scrolling**: Handles thousands of messages efficiently
- **Lazy Loading**: Components load on demand
- **Service Worker**: Offline capability for field operations

## 🧪 Testing

```bash
# Type checking
npm run check

# Linting
npm run lint

# Format code
npm run format
```

## 🤝 Contributing

1. Follow TypeScript strict mode requirements
2. Use the established OSINT design system
3. Maintain component composition patterns
4. Test WebSocket integration thoroughly

---

**Built for GeopolMonitor** - Professional intelligence monitoring platform 