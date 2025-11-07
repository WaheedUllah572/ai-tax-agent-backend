import { useState } from "react";
import axios from "axios";

// ✅ Helper for safely displaying nested or null values
const safeValue = (val) => {
  if (!val) return "—";
  if (typeof val === "object") {
    return (
      val.Name ||
      val.DisplayName ||
      val.value ||
      val.FreeFormNumber ||
      JSON.stringify(val)
    );
  }
  return val;
};

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL?.trim() ||
  window?.__API_BASE_URL__?.trim() ||
  "https://symbols-superb-icons-exhibitions.trycloudflare.com";

export default function Expenses() {
  const [form, setForm] = useState({ Vendor: "", Amount: "", Category: "" });
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isNaN(parseFloat(form.Amount))) {
        setResponse({ error: "Amount must be a valid number." });
        setLoading(false);
        return;
      }

      const res = await axios.post(`${BASE_URL}/quickbooks/expenses`, form, {
        headers: { "Content-Type": "application/json" },
      });
      setResponse(res.data);
    } catch (err) {
      const errMsg =
        err.response?.data?.error ||
        "QuickBooks API failed. Please check account type or reconnect QuickBooks.";
      setResponse({ error: errMsg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 bg-gradient-to-br from-purple-50 via-white to-pink-50 min-h-screen">
      <h2 className="text-3xl font-bold text-gray-800 mb-6">Add Expense</h2>

      <form
        onSubmit={handleSubmit}
        className="max-w-md mx-auto bg-white p-6 rounded-xl shadow-lg space-y-4"
      >
        <input
          name="Vendor"
          placeholder="Vendor Name"
          value={form.Vendor}
          onChange={handleChange}
          className="w-full border p-3 rounded-md focus:ring-2 focus:ring-purple-400"
        />
        <input
          name="Amount"
          placeholder="Amount"
          type="number"
          value={form.Amount}
          onChange={handleChange}
          className="w-full border p-3 rounded-md focus:ring-2 focus:ring-purple-400"
        />
        <input
          name="Category"
          placeholder="Category (e.g., Bank Charges)"
          value={form.Category}
          onChange={handleChange}
          className="w-full border p-3 rounded-md focus:ring-2 focus:ring-purple-400"
        />
        <button
          type="submit"
          disabled={loading}
          className={`w-full text-white p-3 rounded-md transition-all ${
            loading
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-purple-600 hover:bg-purple-700"
          }`}
        >
          {loading ? "Submitting..." : "Add Expense"}
        </button>
      </form>

      {response && (
        <div
          className={`mt-6 p-4 rounded-xl shadow-lg border text-sm ${
            response.error
              ? "bg-red-50 text-red-700 border-red-200"
              : "bg-green-50 text-green-700 border-green-200"
          }`}
        >
          <h3 className="font-semibold mb-2">
            {response.error ? "❌ Error" : "✅ Success"}
          </h3>
          <pre className="text-xs whitespace-pre-wrap break-words">
            {JSON.stringify(response, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
