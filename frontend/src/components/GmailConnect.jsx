import React, { useState } from "react";
import axios from "axios";

const baseURL =
  process.env.REACT_APP_API_BASE_URL ||
  window?.__API_BASE_URL__ ||
  "https://ai-tax-agent-backend-klwl.onrender.com";

export default function GmailConnect() {
  const [year, setYear] = useState(new Date().getFullYear());
  const [receipts, setReceipts] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleConnect = () => {
    window.open(`${baseURL}/gmail/connect`, "_blank", "width=600,height=800");
  };

  const fetchReceipts = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${baseURL}/gmail/receipts?year=${year}`);
      setReceipts(res.data.receipts || []);
    } catch (err) {
      console.error(err);
      alert("Failed to fetch receipts.");
    }
    setLoading(false);
  };

  return (
    <div className="p-6 bg-white rounded-2xl shadow-md text-center">
      <h2 className="text-2xl font-semibold text-indigo-700 mb-4">
        Gmail Receipt Scanner 📧
      </h2>

      <div className="flex flex-col items-center gap-3">
        <button
          onClick={handleConnect}
          className="px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition"
        >
          Connect Gmail
        </button>

        <div className="flex items-center gap-2 mt-4">
          <label className="font-medium">Tax Year:</label>
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            className="border rounded px-2 py-1 w-24 text-center"
          />
          <button
            onClick={fetchReceipts}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Fetch Receipts
          </button>
        </div>
      </div>

      {loading && <p className="mt-6 text-gray-500">Scanning emails...</p>}

      <div className="mt-6 text-left">
        {receipts.map((r, i) => (
          <div
            key={i}
            className="border border-gray-200 rounded-lg p-3 mb-3 shadow-sm"
          >
            <p className="text-gray-700 text-sm">{r.email_snippet}</p>
            <pre className="bg-gray-50 text-xs mt-2 p-2 rounded overflow-auto">
              {r.analysis}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}
