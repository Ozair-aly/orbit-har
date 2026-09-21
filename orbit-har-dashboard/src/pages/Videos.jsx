import { useEffect, useState } from "react";

const BASE_URL = "https://orbit-har-1.onrender.com";
const VIDEOS_URL = `${BASE_URL}/videos`;

function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return "--";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function Videos() {

  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [playing, setPlaying] = useState(null);

  const fetchVideos = async () => {
    try {
      const response = await fetch(VIDEOS_URL);

      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }

      const result = await response.json();
      setVideos(Array.isArray(result) ? result : result.videos || []);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch videos:", err);
      setError("Could not reach the videos backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideos();
  }, []);

  return (
    <main className="page">

      <section className="panel videos-panel">

        <div className="panel-title">
          <span>RECORDED VIDEOS</span>
          <button className="refresh-btn" onClick={fetchVideos}>↻ Refresh</button>
        </div>

        {loading ? (
          <div className="empty">Loading videos...</div>
        ) : error ? (
          <div className="empty">
            {error}
            <br />
            <small>Expecting a GET endpoint at /videos on your backend.</small>
          </div>
        ) : videos.length === 0 ? (
          <div className="empty">No recordings yet. Start a recording from the Monitoring page.</div>
        ) : (
          <div className="video-grid">
            {videos.map((video, index) => (
              <div className="video-card" key={video.filename || index}>

                <div className="video-thumb" onClick={() => setPlaying(video)}>
                  <span className="video-play-icon">▶</span>
                </div>

                <div className="video-meta">
                  <strong>{video.filename || `recording_${index + 1}.mp4`}</strong>
                  <span>{video.timestamp || video.created_at || "--"}</span>
                  <span>
                    {video.duration ? `${video.duration}` : "--"} · {formatBytes(video.size)}
                  </span>
                </div>

              </div>
            ))}
          </div>
        )}

      </section>

      {playing && (
        <div className="video-modal-backdrop" onClick={() => setPlaying(null)}>
          <div className="video-modal" onClick={(e) => e.stopPropagation()}>

            <div className="video-modal-header">
              <strong>{playing.filename}</strong>
              <button className="video-modal-close" onClick={() => setPlaying(null)}>✕</button>
            </div>

            <video
              className="video-player"
              src={`${BASE_URL}/videos/${playing.filename}`}
              controls
              autoPlay
            />

          </div>
        </div>
      )}

    </main>
  );
}

export default Videos;
