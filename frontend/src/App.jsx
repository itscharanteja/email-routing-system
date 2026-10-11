import React, { useState, useEffect } from "react";
import "./App.css";

const API = "http://localhost:8000/api";

export default function App() {
  const [data, setData] = useState({ team_queue: [], review_queue: [], training_data: [] });
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [selectedTeams, setSelectedTeams] = useState({});

  const loadData = async () => {
    try {
      const res = await fetch(`${API}/data`);
      if (res.ok) setData(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 2000);
    return () => clearInterval(timer);
  }, []);

  const sendEmail = async (sub, txt) => {
    const s = sub !== undefined ? sub : subject;
    const b = txt !== undefined ? txt : body;
    if (!s || !b) return;

    await fetch(`${API}/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender: "user@example.com", subject: s, body: b })
    });
    setSubject("");
    setBody("");
    loadData();
  };

  const reviewEmail = async (index, team) => {
    await fetch(`${API}/human-review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email_index: index, team: team || "Billing" })
    });
    loadData();
  };

  return (
    <div className="container">
      <header>
        <h1>Email Routing System</h1>
        <p className="subtitle">FastAPI + Lightweight Model + OpenAI API + Human Review + Training Data</p>
      </header>

      {/* Basic Flowchart Display */}
      <div className="flowchart-banner">
{`Email Webhook ➔ FastAPI ➔ Lightweight Model
                           ├─ Confident  ➔ Team Queue
                           └─ Uncertain  ➔ OpenAI LLM
                                           ├─ Confident ➔ Team Queue
                                           └─ Uncertain ➔ Review Queue ➔ Human ➔ Training Data`}
      </div>

      {/* Email Composer & Test Presets */}
      <div className="composer">
        <div style={{ fontWeight: 600, marginBottom: 8, fontSize: "0.9rem" }}>1. Ingest Email (Try a quick preset):</div>
        <div className="quick-buttons">
          <button className="secondary" onClick={() => sendEmail("Refund invoice #10", "Please refund this receipt.")}>
            ⚡ Test A: "Refund" (Lightweight Confident ➔ Team)
          </button>
          <button className="secondary" onClick={() => sendEmail("Enterprise Pricing & Demo", "We want to schedule a product demo.")}>
            🧠 Test B: "Pricing Demo" (LLM Confident ➔ Team)
          </button>
          <button className="secondary" onClick={() => sendEmail("Vague inquiry", "Need help with something strange.")}>
            ⏳ Test C: "Unclear Issue" (Review Queue ➔ Human ➔ Training Data)
          </button>
        </div>

        <div className="input-row">
          <input
            placeholder="Subject..."
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
        </div>
        <textarea
          rows={2}
          placeholder="Email body text..."
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
        <button onClick={() => sendEmail()}>Send Custom Email</button>
      </div>

      {/* 3 Simple Output Columns */}
      <div className="columns">
        {/* Column 1: Team Queue */}
        <div className="col">
          <h2>
            Team Queue
            <span className="count">{data.team_queue.length}</span>
          </h2>
          {data.team_queue.length === 0 && <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>No routed emails yet.</p>}
          {data.team_queue.map((item, idx) => (
            <div key={idx} className="card">
              <div className="card-title">
                <span className="badge badge-green">{item.team}</span>
                {item.subject}
              </div>
              <div className="card-body">{item.body}</div>
              <span className="badge badge-blue">via {item.routed_by}</span>
            </div>
          ))}
        </div>

        {/* Column 2: Review Queue */}
        <div className="col">
          <h2>
            Review Queue (Human)
            <span className="count">{data.review_queue.length}</span>
          </h2>
          {data.review_queue.length === 0 && <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>Queue is empty.</p>}
          {data.review_queue.map((item, idx) => (
            <div key={idx} className="card" style={{ borderColor: "#fcd34d" }}>
              <div className="card-title">
                <span className="badge badge-amber">Uncertain</span>
                {item.subject}
              </div>
              <div className="card-body">{item.body}</div>
              <div className="triage-box">
                <select
                  value={selectedTeams[idx] || "Billing"}
                  onChange={(e) => setSelectedTeams({ ...selectedTeams, [idx]: e.target.value })}
                >
                  <option value="Billing">Billing</option>
                  <option value="Tech Support">Tech Support</option>
                  <option value="Sales">Sales</option>
                </select>
                <button onClick={() => reviewEmail(idx, selectedTeams[idx] || "Billing")}>
                  Assign & Save
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Column 3: Training Data */}
        <div className="col">
          <h2>
            Training Data
            <span className="count">{data.training_data.length}</span>
          </h2>
          {data.training_data.length === 0 && <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>No human labels yet.</p>}
          {data.training_data.map((item, idx) => (
            <div key={idx} className="card" style={{ borderLeft: "3px solid #8b5cf6" }}>
              <div className="card-title">
                <span className="badge" style={{ background: "#ede9fe", color: "#6d28d9" }}>{item.team}</span>
                {item.subject}
              </div>
              <div className="card-body">{item.body}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
