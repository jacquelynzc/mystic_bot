import React, { useEffect, useState } from "react";
import "./App.css";

function App() {
    const [trends, setTrends] = useState([]);
    const [sortBy, setSortBy] = useState("score");
    const [filterStage, setFilterStage] = useState("all");
    const validStages = new Set(["early", "rising", "niche", "exploding"]);

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

    const filteredTrends = trends.filter(trend => {
    const stage = trend.stage?.toLowerCase();
    return filterStage === "all" || stage === filterStage;
});
    const sortedTrends = [...filteredTrends].sort((a, b) => {
        if (sortBy === "score") return b.score - a.score;
        if (sortBy === "stage") return a.stage.localeCompare(b.stage);
        return 0;
    });

    return (
        <div className="app-container">
            <div className="clouds-background animated-clouds"></div>
            <h1 className="glow-text animated-title">📈 Mystic Trend Oracle</h1>

            <div className="filters modern-filters">
                <div className="filter-group">
                    <label htmlFor="sort">Sort by:</label>
                    <select
                        id="sort"
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                    >
                        <option value="score">Virality Score</option>
                        <option value="stage">Trend Stage</option>
                    </select>
                </div>
                <div className="filter-group">
                    <label htmlFor="stage">Filter by Stage:</label>
                    <select
                        id="stage"
                        value={filterStage}
                        onChange={(e) => setFilterStage(e.target.value)}
                    >
                        <option value="all">All</option>
                        <option value="early">Early</option>
                        <option value="rising">Rising</option>
                        <option value="niche">Niche</option>
                        <option value="exploding">Exploding</option>
                    </select>
                </div>
            </div>

            <div className="grid">
                {sortedTrends.length > 0 ? (
                    sortedTrends.map((trend, index) => (
                        <div key={index} className={`card hover-effect stage-${trend.stage}`}>
                            <h2>{trend.name}</h2>
                            <p><strong>🔥 Score:</strong> {trend.score}</p>
<p>
  <strong>⏳ Stage:</strong>{" "}
  {(() => {
    if (!trend.stage) return "Unknown";
    const stage = trend.stage.toLowerCase();
    const stageMap = {
      early: "🌱 Early",
      rising: "📈 Rising",
      niche: "🧬 Niche",
      exploding: "💥 Exploding",
    };
    return stageMap[stage] || trend.stage;
  })()}
</p>

<div className="summary-block">
                                <p><strong>🧠 Summary:</strong></p>
                                <p>{trend.summary}</p>
                            </div>
                            {trend.examples && trend.examples.length > 0 && (
                                <div className="examples">
                                    <p><strong>🎬 Examples:</strong></p>
                                    <ul>
                                        {trend.examples.map((example, idx) => (
                                            <li key={idx}>{example}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            {trend.url && (
                                <a href={trend.url} target="_blank" rel="noopener noreferrer">
                                    <button className="view-source-btn">🔗 View Source</button>
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

