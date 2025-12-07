import React, { useState, useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

const GUARD_WEBSOCKET_URL = "ws://localhost:8000/ws/alerts";

const LiveChart = () => {
  const [alerts, setAlerts] = useState([]);
  const [isFlashing, setIsFlashing] = useState(false);
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const seriesRef = useRef();

  useEffect(() => {
    // Initialize the chart
    chartRef.current = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        backgroundColor: '#1a1e26',
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2a2e39' },
        horzLines: { color: '#2a2e39' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: true,
      },
    });

    seriesRef.current = chartRef.current.addCandlestickSeries({
        upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
        wickUpColor: '#26a69a', wickDownColor: '#ef5350',
    });

    // Connect to the WebSocket
    const ws = new WebSocket(GUARD_WEBSOCKET_URL);

    ws.onopen = () => {
      console.log("Connected to Guard WebSocket at", GUARD_WEBSOCKET_URL);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Check if it's an alert or market data
      if (data.type === "SPOOFING") {
        console.log("Received alert:", data);
        setAlerts(prevAlerts => [data, ...prevAlerts.slice(0, 9)]); // Keep last 10 alerts
        
        if (data.severity === "HIGH") {
          setIsFlashing(true);
          // Reset the flashing state after the animation duration
          setTimeout(() => setIsFlashing(false), 700);
        }
      }
    };

    ws.onclose = () => {
      console.log("Disconnected from Guard WebSocket");
    };

    ws.onerror = (error) => {
      console.error("WebSocket Error:", error);
    };

    // Cleanup on component unmount
    return () => {
      ws.close();
      chartRef.current.remove();
    };
  }, []);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className={`transition-colors duration-500 ${isFlashing ? 'screen-flash' : ''}`}>
      <main className="p-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Live Chart Section */}
        <div className="lg:col-span-2 bg-gray-800 p-6 rounded-lg shadow-lg">
          <h2 className="text-2xl font-semibold mb-4">Live Market Data (BTC/USD)</h2>
          <div ref={chartContainerRef} className="w-full h-full" />
        </div>

        {/* Alerts Section */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
          <h2 className="text-2xl font-semibold mb-4">Real-time Alerts Feed</h2>
          <div className="space-y-4">
            {alerts.length === 0 && (
              <p className="text-gray-400">No alerts detected yet. Monitoring...</p>
            )}
            {alerts.map((alert, index) => (
              <div key={index} className={`p-4 rounded-md border ${alert.severity === "HIGH" ? 'bg-red-900 border-red-700' : 'bg-yellow-800 border-yellow-600'}`}>
                <div className="font-bold text-lg">{alert.type}</div>
                <div className="text-sm text-gray-300">{alert.details || 'No details provided.'}</div>
                <div className="text-xs text-gray-400 mt-2">
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
};

export default LiveChart;
