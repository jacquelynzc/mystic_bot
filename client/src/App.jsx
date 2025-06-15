import React, { useEffect, useState } from "react";
import "./App.css";

function MysticApp() {
  const [trends, setTrends] = useState([]);
  const [sortBy, setSortBy] = useState("score");
  const [filterStage, setFilterStage] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [timeframe, setTimeframe] = useState("24h");
  const [selectedDate, setSelectedDate] = useState("");
  const [selectedTrend, setSelectedTrend] = useState(null);

  useEffect(() => {
    setIsLoading(true);
    let url = `http://localhost:8000/trends?timeframe=${timeframe}`;
    if (selectedDate) url += `&date=${selectedDate}`;
    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setTrends(data);
        }
        setIsLoading(false);
      })
      .catch((error) => {
        console.error("Failed to fetch trends:", error);
        setIsLoading(false);
      });
  }, [timeframe, selectedDate]);

  const filteredTrends = trends.filter((trend) => {
    const stage = trend.stage?.toLowerCase();
    return filterStage === "all" || stage === filterStage;
  });

  const sortedTrends = [...filteredTrends].sort((a, b) => {
    if (sortBy === "score") return b.score - a.score;
    if (sortBy === "stage") return a.stage.localeCompare(b.stage);
    return 0;
  });

  return (
    <div>
      <h1>📈 Mystic Trend Oracle</h1>

      <div className="filters">
        <div>
          <label htmlFor="sort">Sort by</label>
          <select id="sort" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="score">Virality Score</option>
            <option value="stage">Trend Stage</option>
          </select>
        </div>

        <div>
          <label htmlFor="stage">Filter Stage</label>
          <select id="stage" value={filterStage} onChange={(e) => setFilterStage(e.target.value)}>
            <option value="all">All</option>
            <option value="early">Early</option>
            <option value="rising">Rising</option>
            <option value="niche">Niche</option>
            <option value="exploding">Exploding</option>
          </select>
        </div>

        <div>
          <label htmlFor="timeframe">Timeframe</label>
          <select id="timeframe" value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
            <option value="24h">Last 24h</option>
            <option value="3d">Last 3 days</option>
            <option value="7d">Last 7 days</option>
          </select>
        </div>

        <div>
          <label htmlFor="date">Date</label>
          <input type="date" id="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} />
        </div>
      </div>

      <div className="grid">
        {isLoading ? (
          [...Array(6)].map((_, i) => <div key={i} className="shimmer"></div>)
        ) : sortedTrends.length > 0 ? (
          sortedTrends.map((trend, index) => (
            <div key={index} className="card" onClick={() => setSelectedTrend(trend)}>
              <h2>#{index + 1} {trend.name}</h2>
              <hr />
              <p><strong>🔥 Score:</strong> {trend.score} ({trend.percent_change || 0}%)</p>
              <p><strong>⏳ Stage:</strong> {trend.stage}</p>
            </div>
          ))
        ) : (
          <p style={{ textAlign: "center" }}>✨ No trends found yet.</p>
        )}
      </div>

      {selectedTrend && (
        <div className="modal-backdrop" onClick={() => setSelectedTrend(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="close" onClick={() => setSelectedTrend(null)}>&times;</button>
            <h2>{selectedTrend.name}</h2>
            <hr />
            <p><strong>🔥 Score:</strong> {selectedTrend.score} ({selectedTrend.percent_change || 0}%)</p>
            <p><strong>⏳ Stage:</strong> {selectedTrend.stage}</p>
            <div>
              <p><strong>🧠 Summary:</strong> {selectedTrend.summary}</p>
            </div>
            {selectedTrend.examples?.length > 0 && (
              <div>
                <p><strong>🎬 Examples:</strong></p>
                <ul>
                  {selectedTrend.examples.map((example, idx) => <li key={idx}>{example}</li>)}
                </ul>
              </div>
            )}
            {selectedTrend.url && (
              <a href={selectedTrend.url} target="_blank" rel="noopener noreferrer">
                <button className="view-source-btn">🔗 View Source</button>
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default MysticApp;

