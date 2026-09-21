import { useEffect, useState } from "react";
import { BACKEND_URL } from "../config.js";


function TextFiles() {

  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);

  // ==========================================
  // LOAD FILE LIST
  // ==========================================

  const loadFiles = async () => {

    try {

      setLoading(true);

      const response = await fetch(
        `${BACKEND_URL}/text-files`
      );

      const data = await response.json();

      if (data.status === "success") {
        setFiles(data.files);
      }

    } catch (error) {

      console.error(
        "Failed to load text files:",
        error
      );

    } finally {

      setLoading(false);

    }
  };


  // ==========================================
  // LOAD FILE CONTENT
  // ==========================================

  const openFile = async (filename) => {

    try {

      const response = await fetch(
        `${BACKEND_URL}/text-files/${encodeURIComponent(filename)}`
      );

      const data = await response.json();

      if (data.status === "success") {

        setSelectedFile(data.name);
        setContent(data.content);

      }

    } catch (error) {

      console.error(
        "Failed to open text file:",
        error
      );

    }
  };


  useEffect(() => {

    loadFiles();

  }, []);


  return (

    <div className="text-files-page">

      <div className="page-title">

        <h2>Text Files</h2>

        <p>
          Local experiment logs stored on the
          astronaut-side system.
        </p>

      </div>


      <div className="text-files-layout">

        {/* =====================================
            FILE LIST
        ===================================== */}

        <div className="text-file-list">

          <div className="section-header">

            <h3>LOCAL LOG FILES</h3>

            <button
              onClick={loadFiles}
              type="button"
            >
              ↻ Refresh
            </button>

          </div>


          {loading && (

            <div className="empty-files">
              Loading files...
            </div>

          )}


          {!loading && files.length === 0 && (

            <div className="empty-files">

              No text log files found.

            </div>

          )}


          {files.map((file) => (

            <button
              key={file.name}
              className={
                selectedFile === file.name
                  ? "text-file-item selected"
                  : "text-file-item"
              }
              onClick={() =>
                openFile(file.name)
              }
              type="button"
            >

              <div className="file-icon">
                📄
              </div>

              <div className="file-info">

                <strong>
                  {file.name}
                </strong>

                <span>
                  {file.modified}
                </span>

              </div>

            </button>

          ))}

        </div>


        {/* =====================================
            FILE VIEWER
        ===================================== */}

        <div className="text-file-viewer">

          {selectedFile ? (

            <>

              <div className="viewer-header">

                <div>

                  <span>
                    SELECTED FILE
                  </span>

                  <h3>
                    {selectedFile}
                  </h3>

                </div>

              </div>


              <pre className="log-content">
                {content}
              </pre>

            </>

          ) : (

            <div className="viewer-empty">

              <div className="viewer-icon">
                📜
              </div>

              <h3>
                No file selected
              </h3>

              <p>
                Select a local text log to view
                its contents.
              </p>

            </div>

          )}

        </div>

      </div>

    </div>

  );
}

export default TextFiles;