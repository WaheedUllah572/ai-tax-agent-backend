import { useEffect, useState } from "react";
import axios from "axios";

// ✅ Helper for safely displaying nested or null values
const safeValue = (val) => {
  if (!val) return "—";
  if (typeof val === "object") {
    return (
      val.Name ||
      val.value ||
      val.FreeFormNumber ||
      JSON.stringify(val)
    );
  }
  return val;
};

export default function Accounts() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);

  const BASE_URL =
    process.env.REACT_APP_API_BASE_URL?.trim() ||
    window?.__API_BASE_URL__?.trim() ||
    "https://symbols-superb-icons-exhibitions.trycloudflare.com";

  useEffect(() => {
    axios
      .get(`${BASE_URL}/quickbooks/accounts`)
      .then((res) => setAccounts(res.data.accounts || []))
      .catch((err) => console.error("Error fetching accounts:", err.message))
      .finally(() => setLoading(false));
  }, [BASE_URL]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-yellow-50 via-white to-amber-50">
        <p className="text-lg text-gray-600">Loading QuickBooks Accounts...</p>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gradient-to-br from-yellow-50 via-white to-amber-50 min-h-screen">
      <h2 className="text-3xl font-bold text-gray-800 mb-6">
        QuickBooks Accounts
      </h2>

      {accounts.length === 0 ? (
        <p className="text-gray-600 text-lg">No accounts found in QuickBooks.</p>
      ) : (
        <table className="w-full border border-gray-200 rounded-lg shadow-lg">
          <thead className="bg-yellow-600 text-white">
            <tr>
              <th className="p-3 text-left">Account Name</th>
              <th className="p-3 text-left">Type</th>
              <th className="p-3 text-left">Subtype</th>
              <th className="p-3 text-left">Balance</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((acc, i) => (
              <tr key={i} className="odd:bg-white even:bg-yellow-50">
                <td className="p-3">{safeValue(acc.Name)}</td>
                <td className="p-3">{safeValue(acc.AccountType)}</td>
                <td className="p-3">{safeValue(acc.AccountSubType)}</td>
                <td className="p-3">${safeValue(acc.CurrentBalance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
