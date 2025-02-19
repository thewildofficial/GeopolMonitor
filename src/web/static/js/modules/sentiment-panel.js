export class SentimentPanel {
    constructor() {
        this.panel = null;
        this.currentCountry = null;
        this.init();
    }

    init() {
        this.createPanel();
        this.setupEventListeners();
    }

    createPanel() {
        const panel = document.createElement('div');
        panel.className = 'sentiment-panel';
        panel.innerHTML = `
            <div class="sentiment-header">
                <h3>Sentiment Analysis</h3>
            </div>
            <div class="sentiment-content">
                <div class="sentiment-score">
                    <div class="score-circle">0.0</div>
                    <div class="score-details">
                        <div class="score-label">Overall Sentiment</div>
                        <div class="score-value">Neutral</div>
                    </div>
                </div>
                <div class="bias-section">
                    <div class="bias-header">Source Bias Analysis</div>
                    <div class="bias-list"></div>
                </div>
            </div>
        `;
        document.querySelector('.map-container').appendChild(panel);
        this.panel = panel;
    }

    setupEventListeners() {
        // Mobile touch handling
        if (window.matchMedia('(max-width: 768px)').matches) {
            let startY = 0;
            let currentY = 0;

            this.panel.addEventListener('touchstart', (e) => {
                startY = e.touches[0].clientY;
                this.panel.style.transition = 'none';
            });

            this.panel.addEventListener('touchmove', (e) => {
                currentY = e.touches[0].clientY;
                const deltaY = currentY - startY;
                if (deltaY > 0) { // Only allow downward swipe
                    this.panel.style.transform = `translateY(${deltaY}px)`;
                }
            });

            this.panel.addEventListener('touchend', () => {
                this.panel.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
                if (currentY - startY > 100) {
                    this.hide();
                } else {
                    this.panel.style.transform = '';
                }
            });
        }
    }

    updateSentiment(data) {
        const { sentiment, biases } = data;
        const scoreCircle = this.panel.querySelector('.score-circle');
        const scoreValue = this.panel.querySelector('.score-value');
        
        // Update sentiment score
        scoreCircle.textContent = sentiment.toFixed(1);
        scoreCircle.style.background = this.getSentimentGradient(sentiment);
        scoreValue.textContent = this.getSentimentLabel(sentiment);

        // Update bias list
        const biasList = this.panel.querySelector('.bias-list');
        biasList.innerHTML = biases.map(bias => `
            <div class="bias-item">
                <div class="bias-icon">${this.getBiasIcon(bias.type)}</div>
                <div class="bias-details">
                    <div class="bias-type">${bias.type}</div>
                    <div class="bias-value">${bias.value}</div>
                </div>
            </div>
        `).join('');
    }

    getSentimentGradient(score) {
        if (score > 0.3) return 'linear-gradient(135deg, #34c759, #30d158)';
        if (score < -0.3) return 'linear-gradient(135deg, #ff453a, #ff3b30)';
        return 'linear-gradient(135deg, #ffb340, #ffa000)';
    }

    getSentimentLabel(score) {
        if (score > 0.3) return 'Positive';
        if (score < -0.3) return 'Negative';
        return 'Neutral';
    }

    getBiasIcon(type) {
        const icons = {
            'western': '🌎',
            'russian': '🇷🇺',
            'chinese': '🇨🇳',
            'israeli': '🇮🇱',
            'turkish': '🇹🇷',
            'arab': '🌍'
        };
        return icons[type.toLowerCase()] || '📰';
    }

    show() {
        this.panel.classList.add('active');
    }

    hide() {
        this.panel.classList.remove('active');
    }
}