// Base JavaScript functionality

// WebSocket connection management
class WebSocketManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second delay
    }

    connect(path) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${path}`;

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('WebSocket connection established');
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.updateConnectionStatus(true);
        };

        this.socket.onclose = () => {
            console.log('WebSocket connection closed');
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus(false);
        };

        return this.socket;
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => {
                console.log(`Attempting to reconnect... (${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
                this.connect();
                this.reconnectAttempts++;
                this.reconnectDelay *= 2; // Exponential backoff
            }, this.reconnectDelay);
        } else {
            console.log('Max reconnection attempts reached');
        }
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('websocket-status');
        if (statusElement) {
            statusElement.className = connected ? 'connected' : 'disconnected';
            statusElement.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }

    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        }
    }
}

// Theme management
class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('theme') || 'system';
        this.initialize();
    }

    initialize() {
        this.applyTheme();
        this.setupThemeToggle();
        this.setupSystemThemeListener();
    }

    applyTheme() {
        const isDark = this.theme === 'dark' || 
            (this.theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
        
        document.documentElement.classList.toggle('dark-theme', isDark);
    }

    setupThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.theme = this.theme === 'dark' ? 'light' : 'dark';
                localStorage.setItem('theme', this.theme);
                this.applyTheme();
            });
        }
    }

    setupSystemThemeListener() {
        window.matchMedia('(prefers-color-scheme: dark)').addListener(() => {
            if (this.theme === 'system') {
                this.applyTheme();
            }
        });
    }
}

// Initialize components when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme manager
    const themeManager = new ThemeManager();

    // Setup smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.addEventListener('mouseenter', e => {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = element.dataset.tooltip;
            document.body.appendChild(tooltip);

            const rect = element.getBoundingClientRect();
            tooltip.style.top = `${rect.bottom + 5}px`;
            tooltip.style.left = `${rect.left + (rect.width - tooltip.offsetWidth) / 2}px`;
        });

        element.addEventListener('mouseleave', () => {
            const tooltip = document.querySelector('.tooltip');
            if (tooltip) {
                tooltip.remove();
            }
        });
    });
});

// Export for use in other modules
window.WebSocketManager = WebSocketManager;
window.ThemeManager = ThemeManager;