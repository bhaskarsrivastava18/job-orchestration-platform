import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, BarChart, Bar
} from "recharts";

const API = "http://localhost:8000";

// ── Colour constants ──────────────────────────────────────
const STATUS_COLORS = {
  pending:  "#F59E0B",
  running:  "#3B82F6",
  done:     "#10B981",
  failed:   "#EF4444",
};

// ── Stat card component ───────────────────────────────────
function StatCard({ label, value, color, icon }) {
  return (
    <div style={{
      background: "#1E293B",
      border: `1px solid ${color}40`,
      borderLeft: `4px solid ${color}`,
      borderRadius: 8,
      padding: "16px 20px",
      flex: 1,
    }}>
      <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>
        {value}
      </div>
    </div>
  );
}

// ── Job row component ─────────────────────────────────────
function JobRow({ job }) {
  const color = STATUS_COLORS[job.status] || "#94A3B8";
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      padding: "10px 16px",
      borderBottom: "1px solid #1E293B",
      gap: 12,
    }}>
      <div style={{
        width: 8, height: 8,
        borderRadius: "50%",
        background: color,
        flexShrink: 0,
      }} />
      <div style={{ flex: 1, fontSize: 13, color: "#E2E8F0" }}>
        {job.name}
      </div>
      <div style={{
        fontSize: 11,
        color: "#64748B",
        width: 60,
        textAlign: "right"
      }}>
        P{job.priority}
      </div>
      <div style={{
        fontSize: 11,
        color,
        fontWeight: 600,
        width: 70,
        textAlign: "right",
        textTransform: "uppercase",
      }}>
        {job.status}
      </div>
      <div style={{
        fontSize: 10,
        color: "#475569",
        width: 120,
        textAlign: "right",
      }}>
        {job.id.slice(0, 8)}...
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────
export default function App() {
  const [summary, setSummary]     = useState(null);
  const [jobs, setJobs]           = useState([]);
  const [history, setHistory]     = useState([]);
  const [loading, setLoading]     = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [summaryRes, jobsRes] = await Promise.all([
        axios.get(`${API}/metrics/summary`),
        axios.get(`${API}/jobs`),
      ]);
      setSummary(summaryRes.data);
      setJobs(jobsRes.data);
      setLastUpdated(new Date().toLocaleTimeString());
      setLoading(false);

      // Keep rolling history for the chart (last 20 data points)
      setHistory(prev => {
        const point = {
          time: new Date().toLocaleTimeString(),
          queue: summaryRes.data.queue_depth,
          running: summaryRes.data.running,
          done: summaryRes.data.done,
        };
        return [...prev.slice(-19), point];
      });
    } catch (err) {
      console.error("Failed to fetch:", err);
    }
  }, []);

  // Poll every 2 seconds
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Submit a test job
  const submitJob = async () => {
    const names = ["send_email", "process_payment", "generate_report", "send_sms"];
    const name = names[Math.floor(Math.random() * names.length)];
    const priority = Math.floor(Math.random() * 10) + 1;
    try {
      await axios.post(`${API}/jobs`, {
        name,
        description: `Test job submitted from dashboard`,
        priority,
      });
    } catch (err) {
      alert(err.response?.data?.detail || "Error submitting job");
    }
  };

  if (loading) {
    return (
      <div style={{
        height: "100vh", display: "flex",
        alignItems: "center", justifyContent: "center",
        background: "#0F172A", color: "#94A3B8", fontSize: 16,
      }}>
        Connecting to Job Orchestration Platform...
      </div>
    );
  }

  return (
    <div style={{
      background: "#0F172A",
      minHeight: "100vh",
      color: "#E2E8F0",
      fontFamily: "'Inter', 'Segoe UI', sans-serif",
      padding: "24px 32px",
    }}>

      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between",
        alignItems: "center", marginBottom: 28,
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "#F1F5F9" }}>
            Job Orchestration Platform
          </h1>
          <div style={{ fontSize: 12, color: "#475569", marginTop: 4 }}>
            Live dashboard · Updates every 2 seconds · Last updated: {lastUpdated}
          </div>
        </div>
        <button
          onClick={submitJob}
          style={{
            background: "#0D9488",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "10px 20px",
            cursor: "pointer",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          + Submit Test Job
        </button>
      </div>

      {/* Stat cards */}
      <div style={{ display: "flex", gap: 16, marginBottom: 28 }}>
        <StatCard
          label="Queue Depth"
          value={summary?.queue_depth ?? 0}
          color="#F59E0B"
        />
        <StatCard
          label="Running"
          value={summary?.running ?? 0}
          color="#3B82F6"
        />
        <StatCard
          label="Completed"
          value={summary?.done ?? 0}
          color="#10B981"
        />
        <StatCard
          label="Failed"
          value={summary?.failed ?? 0}
          color="#EF4444"
        />
        <StatCard
          label="Total Jobs"
          value={summary?.total_jobs ?? 0}
          color="#8B5CF6"
        />
      </div>

      {/* Charts row */}
      <div style={{ display: "flex", gap: 20, marginBottom: 28 }}>

        {/* Live queue chart */}
        <div style={{
          flex: 2,
          background: "#1E293B",
          borderRadius: 10,
          padding: 20,
          border: "1px solid #334155",
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: "#94A3B8" }}>
            Queue Depth + Running Jobs (live)
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#475569" }} hide />
              <YAxis tick={{ fontSize: 10, fill: "#475569" }} />
              <Tooltip
                contentStyle={{ background: "#0F172A", border: "1px solid #334155" }}
                labelStyle={{ color: "#94A3B8" }}
              />
              <Line
                type="monotone" dataKey="queue"
                stroke="#F59E0B" strokeWidth={2}
                dot={false} name="Queue"
              />
              <Line
                type="monotone" dataKey="running"
                stroke="#3B82F6" strokeWidth={2}
                dot={false} name="Running"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Status breakdown bar chart */}
        <div style={{
          flex: 1,
          background: "#1E293B",
          borderRadius: 10,
          padding: 20,
          border: "1px solid #334155",
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: "#94A3B8" }}>
            Job Status Breakdown
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={[
              { name: "Pending", count: summary?.pending ?? 0, fill: "#F59E0B" },
              { name: "Running", count: summary?.running ?? 0, fill: "#3B82F6" },
              { name: "Done",    count: summary?.done ?? 0,    fill: "#10B981" },
              { name: "Failed",  count: summary?.failed ?? 0,  fill: "#EF4444" },
            ]}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94A3B8" }} />
              <YAxis tick={{ fontSize: 11, fill: "#94A3B8" }} />
              <Tooltip
                contentStyle={{ background: "#0F172A", border: "1px solid #334155" }}
              />
              <Bar dataKey="count" fill="#0D9488" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Job list */}
      <div style={{
        background: "#1E293B",
        borderRadius: 10,
        border: "1px solid #334155",
        overflow: "hidden",
      }}>
        <div style={{
          display: "flex",
          padding: "12px 16px",
          borderBottom: "1px solid #334155",
          fontSize: 11,
          color: "#475569",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          gap: 12,
        }}>
          <div style={{ width: 8 }} />
          <div style={{ flex: 1 }}>Job Name</div>
          <div style={{ width: 60, textAlign: "right" }}>Priority</div>
          <div style={{ width: 70, textAlign: "right" }}>Status</div>
          <div style={{ width: 120, textAlign: "right" }}>Job ID</div>
        </div>
        {jobs.length === 0 ? (
          <div style={{ padding: 40, textAlign: "center", color: "#475569" }}>
            No jobs yet. Click "Submit Test Job" to start.
          </div>
        ) : (
          jobs.map(job => <JobRow key={job.id} job={job} />)
        )}
      </div>

    </div>
  );
}