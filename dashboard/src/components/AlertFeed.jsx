import React from 'react';

const AlertFeed = ({ alerts }) => {
  return (
    <div className="h-[85vh] overflow-y-auto space-y-3 pr-2">
      {alerts.length === 0 && (
        <div className="text-center text-slate-500 pt-10">
          <p>Stealth Mode: No alerts detected.</p>
          <p>Monitoring feed...</p>
        </div>
      )}
      {alerts.map((alert, index) => {
        // Calculate score percentage for AI_ANOMALY alerts
        const scorePercentage = alert.type === 'AI_ANOMALY' && alert.score 
          ? Math.round(alert.score * 100) 
          : null;
        
        // Determine progress bar color based on score
        const getScoreColor = (score) => {
          if (score >= 0.7) return 'bg-red-500';
          if (score >= 0.5) return 'bg-yellow-500';
          return 'bg-emerald-500';
        };

        return (
          <div
            key={index}
            className={`p-3 rounded-lg border animate-fade-in ${
              alert.severity === 'HIGH'
                ? 'bg-red-900/50 border-red-700'
                : 'bg-yellow-800/50 border-yellow-600'
            }`}
          >
            <div className="flex justify-between items-center">
              <span className="font-bold text-md">
                {alert.type || 'UNKNOWN_ALERT'}
              </span>
              <span
                className={`px-2 py-0.5 text-xs rounded-full ${
                  alert.severity === 'HIGH' ? 'bg-red-500' : 'bg-yellow-500'
                }`}
              >
                {alert.severity || 'N/A'}
              </span>
            </div>

            {/* AI Anomaly Score Visualization */}
            {alert.type === 'AI_ANOMALY' && alert.score !== undefined && (
              <div className="mt-3 bg-slate-800/50 p-2 rounded">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-slate-400">🤖 AI Model Confidence</span>
                  <span className="text-xs font-bold text-slate-300">{scorePercentage}%</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${getScoreColor(alert.score)}`}
                    style={{ width: `${scorePercentage}%` }}
                  />
                </div>
                {alert.model && (
                  <p className="text-xs text-slate-500 mt-1">Model: {alert.model}</p>
                )}
                {alert.threshold && (
                  <p className="text-xs text-slate-400 mt-1">
                    Threshold: {Math.round(alert.threshold * 100)}%
                  </p>
                )}
              </div>
            )}

            <p className="text-sm text-slate-300 mt-2">
              {alert.details || `Manipulation detected for ${alert.symbol}`}
            </p>
            {alert.price && (
              <p className="text-xs text-emerald-400 mt-1">
                Price: ${alert.price.toFixed(2)}
              </p>
            )}
            <p className="text-xs text-slate-500 mt-2">
              {new Date(alert.timestamp).toLocaleTimeString()}
            </p>
          </div>
        );
      })}
    </div>
  );
};

export default AlertFeed;
