import { useEffect, useState } from "react";

const LOGS_URL = "http://127.0.0.1:8000/logs";

const FILTERS = [
  { key: "ALL", label: "All" },
  { key: "SUCCESS", label: "Success" },
  { key: "WRONG", label: "Wrong" },
];

function Logs() {

  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("ALL");

  const fetchLogs = async () => {
    try {
      const response = await fetch(LOGS_URL);

      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }

      const result = await response.json();
      setLogs(Array.isArray(result) ? result : result.logs || []);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch logs:", err);
      setError("Could not reach the logs backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  const filteredLogs =
    filter === "ALL" ? logs : logs.filter((log) => log.status === filter);

  return (
    <main className="page">

      <section className="panel logs-panel">

        <div className="panel-title">
          <span>EXPERIMENT LOGS</span>
          <button className="refresh-btn" onClick={fetchLogs}>↻ Refresh</button>
        </div>

        <div className="logs-filters">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={filter === f.key ? "filter-chip active" : "filter-chip"}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="empty">Loading logs...</div>
        ) : error ? (
          <div className="empty">
            {error}
            <br />
            <small>Expecting a GET endpoint at /logs on your backend.</small>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="empty">No logs to show yet.</div>
        ) : (
          <div className="logs-table">

            <div className="logs-row logs-header">
              <b><b><span>Time</span></b></b>
              <b><span>Experiment</span></b>
              <b><span>Step</span></b>
              
              <b><span>Action</span></b>
              <b><span>Status</span></b>
            </div>

            {filteredLogs.map((log, index) => (
              <div className="logs-row" key={index}>
                <b><span>{log.time || "--"}</span></b>
                <span>{log.experiment || "--"}</span>
                <span>{log.step ?? "--"}</span>
                <strong>
                  {log.instruction || log.action || "--"}
                </strong>
                <b className={log.status === "WRONG" ? "detected-wrong" : "detected-state"}>
                  {log.status === "SUCCESS" ? "✓ SUCCESS" : log.status === "WRONG" ? "⚠ WRONG" : log.status || "--"}
                </b>
              </div>
            ))}

          </div>
        )}

      </section>

    </main>
  );
}

export default Logs;
