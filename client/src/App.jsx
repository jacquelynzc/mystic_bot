import React, { useEffect, useState } from "react";
import "./App.css";

function App() {
    const [trends, setTrends] = useState([]);

    useEffect(() => {
        fetch("http://localhost:8000/trends")
            .then((res) => res.json())
            .then((data) => {
                if (Array.isArray(data)) {
                    setTrends(data);
                } else {
                    console.error("Unexpected data format:", data);
                }
            })
            .catch((error) => console.error("❌ Failed to fetch trends:", error));
    }, []);

    return (
        <div className="app-container">
            <h1 className="glow-text">📈 Mystic Trend Oracle</h1>
            <div className="filters">
                {/* Filters coming soon */}
            </div>
            <div className="grid">
                {trends.length > 0 ? (
                    trends.map((trend, index) => (
                        <div key={index} className="card">
                            <h2>{trend.name}</h2>
                            <p><strong>Score:</strong> {trend.score}</p>
                            <p><strong>Stage:</strong> {trend.stage}</p>
                            <div className="summary-block">
                                <p><strong>Summary:</strong></p>
                                <p>{trend.summary}</p>
                            </div>
                            {trend.examples && trend.examples.length > 0 && (
                                <div className="examples">
                                    <p><strong>Examples:</strong></p>
                                    <ul>
                                        {trend.examples.map((example, idx) => (
                                            <li key={idx}>{example}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            {trend.url && (
                                <a href={trend.url} target="_blank" rel="noopener noreferrer">
                                    <button className="view-source-btn">View Source</button>
                                </a>
                            )}
                        </div>
                    ))
                ) : (
                    <p className="no-trends">✨ No trends found yet. Run the bot to populate data.</p>
                )}
            </div>
        </div>
    );
}

export default App;

