import { useEffect, useState } from "react";
import axios from "axios";

// ✅ Helper for safely displaying nested or null values
const safeValue = (val) => {
  if (!val) return "—";
  if (typeof val === "object") {
    return (
      val.DisplayName ||
      val.Name ||
      val.value ||
      val.FreeFormNumber ||
      JSON.stringify(val)
    );
  }
  return val;
};

export default function CompanyInfo() {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);

  const BASE_URL =
    process.env.REACT_APP_API_BASE_URL?.trim() ||
    window?.__API_BASE_URL__?.trim() ||
    "https://symbols-superb-icons-exhibitions.trycloudflare.com";

  useEffect(() => {
    axios
      .get(`${BASE_URL}/quickbooks/companyinfo`)
      .then((res) => setInfo(res.data))
      .catch((err) => {
        console.error("Error fetching company info:", err.message);
        setError("Failed to fetch company info from QuickBooks.");
      });
  }, [BASE_URL]);

  return (
    <div className="p-8 min-h-screen bg-gradient-to-br from-indigo-50 via-white to-blue-50">
      <h2 className="text-3xl font-bold text-gray-800 mb-6">
        QuickBooks Company Info
      </h2>
      {error ? (
        <p className="text-red-600">{error}</p>
      ) : info ? (
        <pre className="bg-gray-900 text-green-300 p-6 rounded-xl shadow-md overflow-x-auto">
          {JSON.stringify(info, null, 2)}
        </pre>
      ) : (
        <p className="text-gray-600">Loading company info...</p>
      )}
    </div>
  );
}
