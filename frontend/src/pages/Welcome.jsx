import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { logInfo, logWarn, logError } from "../utils/logger";

// Results table component
function ResultsTable({ columns, rows }) {
  if (!columns || columns.length === 0) {
    return <p className="text-gray-600">No results to display</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-indigo-100">
            {columns.map((col, idx) => (
              <th
                key={idx}
                className="border border-gray-300 px-4 py-2 text-left font-semibold text-gray-700"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <tr key={rowIdx} className={rowIdx % 2 === 0 ? "bg-white" : "bg-gray-50"}>
              {row.map((cell, cellIdx) => (
                <td
                  key={cellIdx}
                  className="border border-gray-300 px-4 py-2 text-gray-700"
                >
                  {cell !== null ? String(cell) : <span className="text-gray-400 italic">null</span>}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Welcome() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState([]);
  const [success, setSuccess] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);

  // Query related states
  const [queryPrompt, setQueryPrompt] = useState("");
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState(null);
  const [queryResult, setQueryResult] = useState(null);
  const [queryHistory, setQueryHistory] = useState([]);

  useEffect(() => {
    if (!localStorage.getItem("access")) {
      navigate("/login");
    }
  }, []);

  const handleLogout = () => {
    logInfo("User logout", {});
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    navigate("/login");
  };

  const handleFileChange = (e) => {
    logInfo("File selected for upload", { filename: e.target.files[0]?.name });
    setFile(e.target.files[0]);
    setErrors([]);
    setSuccess(null);
  };

  const handleUpload = async () => {
    if (!file) {
      logWarn("Upload attempted without file selected");
      return;
    }

    logInfo("Upload started", { filename: file.name });
    setLoading(true);
    setErrors([]);
    setSuccess(null);
    setUploadResult(null);

    const formData = new FormData();
    formData.append("upload_file", file);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/upload/file/", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access")}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        logInfo("Upload completed", { filename: file.name, upload_id: data.upload_id });
        setSuccess(`"${data.filename}" uploaded successfully!`);
        setUploadResult(data);
        setFile(null);
        setQueryPrompt("");
        setQueryResult(null);
        setQueryHistory([]);
      } else if (response.status === 422) {
        logWarn("Upload validation failed", { status: 422, errors: data.errors });
        setErrors(data.errors);
      } else if (response.status === 400) {
        logWarn("Upload bad request", { status: 400, errors: data.errors });
        setErrors(data.errors?.upload_file || [{ message: "Invalid file." }]);
      } else if (response.status === 401) {
        logWarn("Upload unauthorized", { status: 401 });
        navigate("/login");
      }
    } catch (err) {
      logError("Upload request failed", { error: err?.message || err });
      setErrors([{ message: "Something went wrong. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const handleQuery = async (e) => {
    e.preventDefault();
    
    if (!queryPrompt.trim() || !uploadResult) {
      logWarn("Query attempted with missing input", { queryPrompt, uploadResult });
      return;
    }

    logInfo("Query started", { table_name: uploadResult.table_name, prompt: queryPrompt });
    setQueryLoading(true);
    setQueryError(null);
    setQueryResult(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/upload/query/", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access")}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          table_name: uploadResult.table_name,
          query_prompt: queryPrompt,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        logInfo("Query executed successfully", { table_name: uploadResult.table_name, prompt: queryPrompt });
        setQueryResult(data);
        setQueryHistory([data, ...queryHistory.slice(0, 9)]);
      } else if (response.status === 401) {
        logWarn("Query unauthorized", { status: 401 });
        navigate("/login");
      } else {
        logWarn("Query failed", { status: response.status, error: data.error });
        setQueryError(data.error || "Failed to execute query");
      }
    } catch (err) {
      logError("Query request failed", { error: err?.message || err });
      setQueryError("Something went wrong. Please try again.");
    } finally {
      setQueryLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-200 via-purple-200 to-pink-200 py-10">
      <div className="max-w-6xl mx-auto px-4">
        
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">🎉 Welcome!</h1>
          <p className="text-gray-600">
            Upload Excel files and query them with natural language
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Upload Section */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-white/80 backdrop-blur-lg shadow-xl rounded-3xl p-8">
              <h2 className="text-xl font-semibold text-gray-700 mb-4">📂 Upload File</h2>

              <div className="space-y-4">
                <input
                  type="file"
                  accept=".xlsx"
                  onChange={handleFileChange}
                  disabled={loading}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 disabled:opacity-50"
                />

                {file && (
                  <p className="text-sm text-gray-600">
                    📄 <span className="font-medium">{file.name}</span>
                  </p>
                )}

                <button
                  onClick={handleUpload}
                  disabled={!file || loading}
                  className="w-full bg-indigo-500 hover:bg-indigo-600 disabled:bg-indigo-300 text-white py-2 rounded-lg transition font-medium"
                >
                  {loading ? "Uploading..." : "Upload"}
                </button>
              </div>

              {success && (
                <div className="mt-4 bg-green-50 border border-green-200 rounded-xl p-4">
                  <p className="text-green-700 text-sm">✅ {success}</p>
                </div>
              )}

              {errors.length > 0 && (
                <div className="mt-4 bg-red-50 border border-red-200 rounded-xl p-4">
                  <p className="text-red-700 font-semibold text-sm mb-2">❌ Errors:</p>
                  <ul className="space-y-1">
                    {errors.map((err, idx) => (
                      <li key={idx} className="text-red-600 text-xs">
                        {err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {uploadResult && (
                <div className="mt-4 bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <p className="text-blue-700 font-semibold text-sm mb-2">📊 Details</p>
                  <p className="text-gray-700 text-xs mb-1">
                    <strong>ID:</strong> {uploadResult.upload_id}
                  </p>
                  <p className="text-gray-700 text-xs">
                    <strong>Rows:</strong> {uploadResult.rows_inserted}
                  </p>
                </div>
              )}

              <div className="mt-4 pt-4 border-t border-gray-200">
                <button
                  onClick={handleLogout}
                  className="w-full bg-red-500 hover:bg-red-600 text-white py-2 rounded-lg transition font-medium"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>

          {/* Query Section */}
          <div className="lg:col-span-2 space-y-4">
            {uploadResult ? (
              <>
                {/* Query Input */}
                <div className="bg-white/80 backdrop-blur-lg shadow-xl rounded-3xl p-8">
                  <h2 className="text-xl font-semibold text-gray-700 mb-4">🔍 Ask Your Data</h2>
                  
                  <form onSubmit={handleQuery} className="space-y-4">
                    <div>
                      <textarea
                        value={queryPrompt}
                        onChange={(e) => setQueryPrompt(e.target.value)}
                        placeholder="E.g., 'Show me all records with salary > 50000' or 'What's the average age?'"
                        disabled={queryLoading}
                        className="w-full h-24 p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100 resize-none"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={queryLoading || !queryPrompt.trim()}
                      className="w-full bg-green-500 hover:bg-green-600 disabled:bg-green-300 text-white py-2 rounded-lg transition font-medium"
                    >
                      {queryLoading ? "Generating & Executing..." : "Execute Query"}
                    </button>
                  </form>

                  {queryError && (
                    <div className="mt-4 bg-red-50 border border-red-200 rounded-xl p-4">
                      <p className="text-red-700 font-semibold text-sm mb-1">❌ Error</p>
                      <p className="text-red-600 text-sm">{queryError}</p>
                    </div>
                  )}
                </div>

                {/* Query Result */}
                {queryResult && (
                  <div className="bg-white/80 backdrop-blur-lg shadow-xl rounded-3xl p-8">
                    <h3 className="text-lg font-semibold text-gray-700 mb-4">📊 Results</h3>
                    
                    <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-600 mb-2">
                        <strong>Your Question:</strong> {queryResult.query_prompt}
                      </p>
                      <p className="text-xs text-gray-600">
                        <strong>Generated SQL:</strong>
                      </p>
                      <pre className="bg-white p-2 rounded text-xs text-gray-700 overflow-x-auto mt-1 border border-gray-300">
                        {queryResult.generated_sql}
                      </pre>
                    </div>

                    <div className="bg-indigo-50 p-4 rounded-lg mb-4">
                      <p className="text-sm text-indigo-700 font-semibold">
                        📈 Found {queryResult.row_count} row{queryResult.row_count !== 1 ? "s" : ""}
                      </p>
                    </div>

                    <ResultsTable 
                      columns={queryResult.columns} 
                      rows={queryResult.rows}
                    />
                  </div>
                )}

                {/* Query History */}
                {queryHistory.length > 1 && (
                  <div className="bg-white/80 backdrop-blur-lg shadow-xl rounded-3xl p-8">
                    <h3 className="text-lg font-semibold text-gray-700 mb-4">📜 Query History</h3>
                    <div className="space-y-2">
                      {queryHistory.slice(1).map((item, idx) => (
                        <button
                          key={idx}
                          onClick={() => setQueryPrompt(item.query_prompt)}
                          className="w-full text-left p-3 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700 transition border border-gray-200"
                        >
                          {item.query_prompt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="bg-white/80 backdrop-blur-lg shadow-xl rounded-3xl p-8 h-64 flex items-center justify-center">
                <div className="text-center">
                  <p className="text-gray-500 text-lg">📤 Upload a file to get started</p>
                  <p className="text-gray-400 text-sm mt-2">Then ask questions about your data</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}