/**
 * OSINT Telegram Feed Component - Modern Intelligence Dashboard
 * Handles real-time Telegram message display with sophisticated card-based UI
 */

class TelegramFeed {
    constructor(options = {}) {
        this.container = typeof options.container === 'string' 
            ? document.querySelector(options.container) 
            : options.container;
        this.emptyStateEl = typeof options.emptyState === 'string'
            ? document.querySelector(options.emptyState)
            : options.emptyState;
        
        this.messages = [];
        this.filteredMessages = [];
        this.relevanceThreshold = 0.3;
        this.connectionStatus = 'disconnected';
        this.maxMessages = 500;
        this.layout = options.layout || 'osint';
        this.enableToasts = options.enableToasts || false;
        
        this.stats = {
            total: 0,
            relevant: 0,
            channels: new Set(),
            avgRelevance: 0,
            messageRate: 0
        };
        
        this.filters = {
            keywords: true,
            date: false,
            language: false,
            relevance: true
        };
        
        this.initializeComponent();
        this.bindEvents();
        this.showEmptyState();
        this.startAnalyticsGraphs();
        
        // Initialize WebSocket if URL provided
        if (options.websocketUrl) {
            this.websocket = new TelegramWebSocket(this, options.websocketUrl);
        }
        
        // Add demo data for testing
        setTimeout(() => this.addDemoData(), 1000);
    }

    initializeComponent() {
        // Initialize stats elements
        this.statsElements = {
            activeChannels: document.getElementById('activeChannels'),
            messageRate: document.getElementById('messageRate')
        };
        
        // Initialize analytics graphs
        this.analyticsGraphs = {
            messageVolume: document.getElementById('messageVolumeGraph'),
            aiAnalysis: document.getElementById('aiAnalysisGraph')
        };
        
        // Initialize connection status
        this.updateConnectionStatus('connecting');
        
        // Initialize map and activity
        this.initializeWorldMap();
        this.initializeActivityList();
    }

    bindEvents() {
        // Message stream interactions
        if (this.container) {
            this.container.addEventListener('click', (e) => this.handleCardInteraction(e));
        }
        
        // Filter interactions are handled in the HTML script section
    }

    addMessage(messageData) {
        const message = this.processMessage(messageData);
        
        // Add to messages array (newest first)
        this.messages.unshift(message);
        this.stats.channels.add(message.channelName);
        
        // Limit messages for performance
        if (this.messages.length > this.maxMessages) {
            this.messages = this.messages.slice(0, this.maxMessages);
        }
        
        this.updateStats();
        this.filterAndRender();
        this.updateAnalytics(message);
        this.updateActivityMap(message);
        
        if (this.enableToasts && message.relevanceScore > 0.7) {
            this.showToast(`High relevance: ${message.channelName}`, 'warning');
        }
    }

    processMessage(messageData) {
        return {
            id: messageData.message_id || Math.random().toString(36).substr(2, 9),
            channelId: messageData.channel_id,
            channelName: messageData.channel?.title || messageData.channel_name || 'Unknown Channel',
            channelUsername: messageData.channel?.username || messageData.channel_username || '',
            text: messageData.text || messageData.raw_text || messageData.message || '',
            date: new Date(messageData.date || messageData.timestamp || Date.now()),
            relevanceScore: parseFloat(messageData.relevance_score) || Math.random() * 0.5 + 0.2,
            sentimentScore: messageData.sentiment_score || (Math.random() * 2 - 1),
            urgencyScore: messageData.urgency_score || Math.random(),
            entities: messageData.entities || {},
            detectedLocations: messageData.detected_locations || [],
            views: messageData.views || Math.floor(Math.random() * 1000),
            forwards: messageData.forwards || Math.floor(Math.random() * 50),
            replies: messageData.replies || Math.floor(Math.random() * 20),
            mediaType: messageData.media_type,
            hasMedia: messageData.has_media || false,
            status: this.getMessageStatus(messageData),
            isNew: true,
            threatLevel: this.calculateThreatLevel(messageData)
        };
    }

    calculateThreatLevel(messageData) {
        const relevance = parseFloat(messageData.relevance_score) || Math.random();
        const urgency = messageData.urgency_score || Math.random();
        
        const combined = (relevance + urgency) / 2;
        
        if (combined > 0.7) return 'high';
        if (combined > 0.4) return 'medium';
        return 'low';
    }

    getMessageStatus(messageData) {
        if (messageData.processed) return 'processed';
        if (messageData.analyzing) return 'analyzing';
        return 'pending';
    }

    filterAndRender() {
        // Apply filters
        this.filteredMessages = this.messages.filter(msg => {
            if (this.filters.relevance && msg.relevanceScore < this.relevanceThreshold) {
                return false;
            }
            // Add more filter logic here
            return true;
        });
        
        this.renderMessageStream();
    }

    renderMessageStream() {
        if (this.filteredMessages.length === 0) {
            this.showEmptyState();
            return;
        }
        
        this.hideEmptyState();
        
        // Take only the most recent 20 messages for performance
        const displayMessages = this.filteredMessages.slice(0, 20);
        
        this.container.innerHTML = displayMessages.map(msg => this.createMessageCard(msg)).join('');
        
        // Add AI analysis cards periodically
        if (displayMessages.length > 5) {
            this.insertAIAnalysisCard();
        }
    }

    createMessageCard(message) {
        const channelInitials = this.generateChannelInitials(message.channelName);
        const timeAgo = this.formatTimeAgo(message.date);
        const threatClass = message.threatLevel;
        const entities = this.extractEntities(message);
        
        return `
            <div class="message-card" data-message-id="${message.id}">
                <div class="message-header">
                    <div class="channel-info">
                        <div class="channel-avatar">${channelInitials}</div>
                        <div class="channel-details">
                            <div class="channel-name">${this.escapeHtml(message.channelName)}</div>
                            <div class="channel-timestamp">${timeAgo}</div>
                        </div>
                    </div>
                    <div class="threat-badge ${threatClass}">${threatClass.toUpperCase()}</div>
                </div>
                
                <div class="message-content">
                    <p class="message-text">${this.highlightEntities(this.escapeHtml(message.text))}</p>
                    ${entities.length > 0 ? `
                        <div class="message-entities">
                            ${entities.map(entity => `<span class="entity-highlight">#${entity}</span>`).join(' ')}
                        </div>
                    ` : ''}
                </div>
                
                <div class="message-metadata">
                    <div class="metadata-icons">
                        <span class="metadata-item">📍 ${message.detectedLocations.slice(0, 2).join(', ') || 'Unknown'}</span>
                        <span class="metadata-item">👁️ ${message.views}</span>
                        <span class="metadata-item">🔄 ${message.forwards}</span>
                        <span class="metadata-item">💬 ${message.replies}</span>
                    </div>
                    <div class="relevance-indicator">
                        <span class="metadata-item">🎯 ${Math.round(message.relevanceScore * 100)}%</span>
                    </div>
                </div>
            </div>
        `;
    }

    insertAIAnalysisCard() {
        const analysisCard = `
            <div class="ai-analysis-card">
                <div class="ai-analysis-header">
                    <span class="ai-icon">🧠</span>
                    <span class="ai-label">AI ANALYSIS</span>
                </div>
                <p class="ai-analysis-text">
                    Detected increased activity in ${this.getTopLocation()}. 
                    Pattern analysis suggests ${this.generateAnalysisInsight()}.
                    Threat assessment: ${this.getOverallThreatLevel()}.
                </p>
            </div>
        `;
        
        // Insert after 3rd message
        const cards = this.container.querySelectorAll('.message-card');
        if (cards.length >= 3) {
            cards[2].insertAdjacentHTML('afterend', analysisCard);
        }
    }

    highlightEntities(text) {
        // Simple entity highlighting for demo
        const keywords = ['military', 'government', 'protest', 'attack', 'conflict', 'crisis'];
        let highlighted = text;
        
        keywords.forEach(keyword => {
            const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
            highlighted = highlighted.replace(regex, `<span class="entity-highlight">${keyword}</span>`);
        });
        
        return highlighted;
    }

    generateChannelInitials(channelName) {
        return channelName
            .split(' ')
            .map(word => word.charAt(0).toUpperCase())
            .slice(0, 2)
            .join('');
    }

    extractEntities(message) {
        // Mock entity extraction
        const entities = [];
        const text = message.text.toLowerCase();
        
        if (text.includes('military') || text.includes('army')) entities.push('military');
        if (text.includes('government') || text.includes('official')) entities.push('government');
        if (text.includes('protest') || text.includes('demonstration')) entities.push('protest');
        if (text.includes('attack') || text.includes('strike')) entities.push('attack');
        
        return entities;
    }

    formatTimeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        
        if (diffMins < 1) return 'now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return date.toLocaleDateString();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    updateStats() {
        this.stats.total = this.messages.length;
        this.stats.relevant = this.messages.filter(m => m.relevanceScore > this.relevanceThreshold).length;
        this.stats.avgRelevance = this.messages.length > 0 
            ? this.messages.reduce((sum, m) => sum + m.relevanceScore, 0) / this.messages.length 
            : 0;
        
        // Update UI elements
        if (this.statsElements.activeChannels) {
            this.statsElements.activeChannels.textContent = this.stats.channels.size;
        }
        
        // Calculate message rate (messages per minute)
        this.calculateMessageRate();
    }

    calculateMessageRate() {
        const oneMinuteAgo = new Date(Date.now() - 60000);
        const recentMessages = this.messages.filter(m => m.date > oneMinuteAgo);
        this.stats.messageRate = recentMessages.length;
        
        if (this.statsElements.messageRate) {
            this.statsElements.messageRate.textContent = this.stats.messageRate;
        }
    }

    startAnalyticsGraphs() {
        this.messageVolumeData = new Array(50).fill(0);
        this.aiAnalysisData = new Array(50).fill(0);
        
        // Update graphs every 2 seconds
        setInterval(() => {
            this.updateGraphs();
        }, 2000);
    }

    updateAnalytics(message) {
        // Update message volume
        this.messageVolumeData.push(1);
        this.messageVolumeData.shift();
        
        // Update AI analysis data (simulate)
        const analysisValue = message.relevanceScore * message.urgencyScore;
        this.aiAnalysisData.push(analysisValue);
        this.aiAnalysisData.shift();
    }

    updateGraphs() {
        this.drawGraph('messageVolumeGraph', this.messageVolumeData, '#00E5FF');
        this.drawGraph('aiAnalysisGraph', this.aiAnalysisData, '#30D1FF');
    }

    drawGraph(canvasId, data, color) {
        const canvas = document.querySelector(`#${canvasId} canvas`);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        // Set line style
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        
        // Draw line
        ctx.beginPath();
        data.forEach((value, index) => {
            const x = (index / (data.length - 1)) * width;
            const y = height - (value * height);
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.stroke();
        
        // Add glow effect
        ctx.shadowColor = color;
        ctx.shadowBlur = 3;
        ctx.stroke();
    }

    initializeWorldMap() {
        // Simple world map with activity dots
        const mapSvg = document.querySelector('.map-svg');
        if (!mapSvg) return;
        
        // Add some demo activity dots
        const dots = [
            { x: 200, y: 120, level: 'high' },
            { x: 400, y: 80, level: 'medium' },
            { x: 600, y: 140, level: 'low' },
            { x: 150, y: 180, level: 'medium' },
            { x: 500, y: 200, level: 'high' }
        ];
        
        dots.forEach(dot => {
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', dot.x);
            circle.setAttribute('cy', dot.y);
            circle.setAttribute('class', `activity-dot ${dot.level}`);
            mapSvg.appendChild(circle);
        });
    }

    initializeActivityList() {
        const activityList = document.getElementById('activityList');
        if (!activityList) return;
        
        const activities = [
            { location: 'Eastern Europe', count: 23 },
            { location: 'Middle East', count: 18 },
            { location: 'Southeast Asia', count: 12 },
            { location: 'North Africa', count: 8 }
        ];
        
        activityList.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <span class="activity-location">${activity.location}</span>
                <span class="activity-count">${activity.count}</span>
            </div>
        `).join('');
    }

    updateActivityMap(message) {
        // Update activity counts and map dots based on new messages
        if (message.detectedLocations && message.detectedLocations.length > 0) {
            // In a real implementation, this would update the map visualization
            console.log('Activity detected in:', message.detectedLocations);
        }
    }

    getTopLocation() {
        // Mock function to get most active location
        const locations = ['Eastern Europe', 'Middle East', 'Southeast Asia', 'North Africa'];
        return locations[Math.floor(Math.random() * locations.length)];
    }

    generateAnalysisInsight() {
        const insights = [
            'potential escalation in regional tensions',
            'increased coordinated information campaigns',
            'possible preparation for significant events',
            'heightened security concerns in the region'
        ];
        return insights[Math.floor(Math.random() * insights.length)];
    }

    getOverallThreatLevel() {
        if (this.stats.avgRelevance > 0.7) return 'HIGH';
        if (this.stats.avgRelevance > 0.4) return 'MEDIUM';
        return 'LOW';
    }

    updateFilters() {
        // Get current filter state
        this.filters.keywords = document.getElementById('filter-keywords')?.checked || false;
        this.filters.date = document.getElementById('filter-date')?.checked || false;
        this.filters.language = document.getElementById('filter-language')?.checked || false;
        this.filters.relevance = document.getElementById('filter-relevance')?.checked || false;
        
        // Re-filter and render
        this.filterAndRender();
    }

    showEmptyState() {
        if (this.emptyStateEl) {
            this.emptyStateEl.style.display = 'flex';
        }
        if (this.container) {
            this.container.style.display = 'none';
        }
    }

    hideEmptyState() {
        if (this.emptyStateEl) {
            this.emptyStateEl.style.display = 'none';
        }
        if (this.container) {
            this.container.style.display = 'flex';
        }
    }

    handleCardInteraction(event) {
        const card = event.target.closest('.message-card');
        if (!card) return;
        
        const messageId = card.dataset.messageId;
        const message = this.messages.find(m => m.id === messageId);
        
        if (message) {
            this.showMessageModal(message);
        }
    }

    showMessageModal(message) {
        const modal = document.getElementById('messageModal');
        const modalContent = document.getElementById('modalContent');
        
        if (!modal || !modalContent) return;
        
        modalContent.innerHTML = `
            <div class="modal-message-details">
                <div class="modal-message-header">
                    <h4>${this.escapeHtml(message.channelName)}</h4>
                    <span class="modal-timestamp">${message.date.toLocaleString()}</span>
                </div>
                
                <div class="modal-message-content">
                    <p>${this.highlightEntities(this.escapeHtml(message.text))}</p>
                </div>
                
                <div class="modal-message-metadata">
                    <div class="metadata-grid">
                        <div class="metadata-row">
                            <strong>Relevance Score:</strong>
                            <span>${Math.round(message.relevanceScore * 100)}%</span>
                        </div>
                        <div class="metadata-row">
                            <strong>Threat Level:</strong>
                            <span class="threat-badge ${message.threatLevel}">${message.threatLevel.toUpperCase()}</span>
                        </div>
                        <div class="metadata-row">
                            <strong>Views:</strong>
                            <span>${message.views}</span>
                        </div>
                        <div class="metadata-row">
                            <strong>Forwards:</strong>
                            <span>${message.forwards}</span>
                        </div>
                        ${message.detectedLocations.length > 0 ? `
                        <div class="metadata-row">
                            <strong>Locations:</strong>
                            <span>${message.detectedLocations.join(', ')}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
        
        modal.style.display = 'flex';
    }

    updateConnectionStatus(status) {
        this.connectionStatus = status;
        const statusEl = document.getElementById('connectionStatusText');
        const statusDot = document.querySelector('#connectionStatus .status-dot');
        
        if (statusEl) {
            statusEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        }
        
        if (statusDot) {
            statusDot.className = `status-dot status-${status}`;
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 3000);
    }

    addDemoData() {
        const demoMessages = [
            {
                channel_name: 'Channel Alpha',
                channel_username: 'channelalpha',
                text: 'Military convoy moving toward borders, joint exercises begin at midnight',
                relevance_score: 0.9,
                urgency_score: 0.8,
                detected_locations: ['Eastern Europe'],
                views: 1250,
                forwards: 89,
                replies: 23
            },
            {
                channel_name: 'Anaxage',
                channel_username: 'anaxage',
                text: 'Large protest against new government policies. Civil unrest in capital',
                relevance_score: 0.85,
                urgency_score: 0.7,
                detected_locations: ['Middle East'],
                views: 892,
                forwards: 45,
                replies: 12
            },
            {
                channel_name: 'Actraccc',
                channel_username: 'actraccc',
                text: 'Cyber attack targeting government agency\'s network affecting infrastructure',
                relevance_score: 0.95,
                urgency_score: 0.9,
                detected_locations: ['North America'],
                views: 567,
                forwards: 78,
                replies: 34
            }
        ];
        
        // Add demo messages with delays
        demoMessages.forEach((msg, index) => {
            setTimeout(() => {
                this.addMessage(msg);
            }, (index + 1) * 2000);
        });
    }
}

/**
 * WebSocket Handler for Real-time Updates
 */
class TelegramWebSocket {
    constructor(telegramFeed, websocketUrl) {
        this.telegramFeed = telegramFeed;
        this.websocketUrl = websocketUrl;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        
        this.connect();
    }

    connect() {
        try {
            this.telegramFeed.updateConnectionStatus('connecting');
            
            this.ws = new WebSocket(this.websocketUrl);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket connected to Telegram feed');
                this.telegramFeed.updateConnectionStatus('connected');
                this.reconnectAttempts = 0;
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('❌ Error parsing WebSocket message:', error);
                }
            };
            
            this.ws.onclose = (event) => {
                console.log('🔌 WebSocket connection closed:', event.code, event.reason);
                this.telegramFeed.updateConnectionStatus('disconnected');
                this.attemptReconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.telegramFeed.updateConnectionStatus('disconnected');
            };
            
        } catch (error) {
            console.error('❌ Failed to create WebSocket connection:', error);
            this.telegramFeed.updateConnectionStatus('disconnected');
            this.attemptReconnect();
        }
    }

    handleMessage(data) {
        console.log('📨 Received Telegram message:', data);
        this.telegramFeed.addMessage(data);
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            
            console.log(`🔄 Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connect();
            }, delay);
        } else {
            console.log('❌ Max reconnection attempts reached');
            this.telegramFeed.updateConnectionStatus('disconnected');
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TelegramFeed, TelegramWebSocket };
} 
} 