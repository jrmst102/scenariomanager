/**
 * WebSocket connection management for real-time participant status.
 */

class StatusWebSocket {
    constructor(problemId) {
        this.problemId = problemId;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnect = 5;
        this.reconnectDelay = 2000;
        this.listeners = [];
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/problems/${this.problemId}/status`;

        try {
            this.ws = new WebSocket(url);

            this.ws.onopen = () => {
                console.log('WS connected');
                this.reconnectAttempts = 0;
                // Start ping interval
                this._pingInterval = setInterval(() => {
                    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send('ping');
                    }
                }, 30000);
            };

            this.ws.onmessage = (event) => {
                if (event.data === 'pong') return;
                try {
                    const data = JSON.parse(event.data);
                    this.listeners.forEach(fn => fn(data));
                } catch (e) {
                    // Ignore non-JSON messages
                }
            };

            this.ws.onclose = () => {
                clearInterval(this._pingInterval);
                if (this.reconnectAttempts < this.maxReconnect) {
                    this.reconnectAttempts++;
                    setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
                } else {
                    console.log('WS: falling back to polling');
                    this._startPolling();
                }
            };

            this.ws.onerror = () => {
                if (this.ws) this.ws.close();
            };
        } catch (e) {
            // WebSocket not available, fall back to polling
            this._startPolling();
        }
    }

    onUpdate(fn) {
        this.listeners.push(fn);
    }

    _startPolling() {
        this._pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/v1/problems/${this.problemId}/participants`);
                if (res.ok) {
                    const data = await res.json();
                    this.listeners.forEach(fn => fn({ type: 'poll', participants: data }));
                }
            } catch (e) {
                // Ignore polling errors
            }
        }, 10000);
    }

    disconnect() {
        if (this.ws) this.ws.close();
        clearInterval(this._pingInterval);
        clearInterval(this._pollInterval);
    }
}

// Export for use
if (typeof window !== 'undefined') {
    window.StatusWebSocket = StatusWebSocket;
}
