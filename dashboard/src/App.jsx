import React, { useState, useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

const GUARD_WEBSOCKET_URL = "ws://localhost:8000/ws/alerts";

function App() {
  const [alerts, setAlerts] = useState([]);
  const [latestPrice, setLatestPrice] = useState(null);
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

    seriesRef.current = chartRef.current.addLineSeries({
      color: '#2962FF',
      lineWidth: 2,
    });

    // Connect to the WebSocket
    const ws = new WebSocket(GUARD_WEBSOCKET_URL);

    ws.onopen = () => {
      console.log("Connected to Guard WebSocket");
    };

    ws.onmessage = (event) => {
      const alert = JSON.parse(event.data);
      console.log("Received alert:", alert);
      setAlerts(prevAlerts => [alert, ...prevAlerts.slice(0, 9)]); // Keep last 10 alerts
      
      if (alert.latest_price) {
        setLatestPrice(alert.latest_price);
        const timestamp = new Date(alert.timestamp).getTime() / 1000;
        seriesRef.current.update({ time: timestamp, value: alert.latest_price });
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
    <div className="bg-gray-900 text-white min-h-screen font-sans">
      <header className="bg-gray-800 p-4 shadow-md">
        <h1 className="text-3xl font-bold text-center text-red-500">
          Project Cerberus - Market Surveillance
        </h1>
      </header>

      <main className="p-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Live Chart Section */}
        <div className="lg:col-span-2 bg-gray-800 p-6 rounded-lg shadow-lg">
          <h2 className="text-2xl font-semibold mb-4">Live Price Chart (SPY)</h2>
          <div ref={chartContainerRef} className="w-full h-full" />
          {latestPrice && (
            <div className="mt-4 text-center text-2xl">
              Latest Price: <span className="font-bold text-green-400">${latestPrice.toFixed(2)}</span>
            </div>
          )}
        </div>

        {/* Alerts Section */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
          <h2 className="text-2xl font-semibold mb-4">Real-Time Alerts</h2>
          <div className="space-y-4">
            {alerts.length === 0 && (
              <p className="text-gray-400">No alerts detected yet. Monitoring...</p>
            )}
            {alerts.map((alert, index) => (
              <div key={index} className="bg-red-900 border border-red-700 p-4 rounded-md animate-pulse">
                <div className="font-bold text-lg">{alert.type}</div>
                <div className="text-sm text-gray-300">{alert.message}</div>
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
}

export default App;
