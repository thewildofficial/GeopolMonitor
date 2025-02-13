let ws;

export function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connection established');
    };
    
    ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'news_update') {
            await window.handleNewsUpdate(data.data);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket connection closed, attempting to reconnect...');
        setTimeout(initWebSocket, 1000);
    };
}