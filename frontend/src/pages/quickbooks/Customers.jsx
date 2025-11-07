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

export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);

  const BASE_URL =
    process.env.REACT_APP_API_BASE_URL?.trim() ||
    window?.__API_BASE_URL__?.trim() ||
    "https://symbols-superb-icons-exhibitions.trycloudflare.com";

  useEffect(() => {
    axios
      .get(`${BASE_URL}/quickbooks/customers`)
      .then((res) => setCustomers(res.data.customers || []))
      .catch((err) => {
        console.error("Error fetching customers:", err.message);
        setCustomers([]);
      })
      .finally(() => setLoading(false));
  }, [BASE_URL]);

  if (loading)
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-green-50 via-white to-emerald-50">
        <p className="text-lg text-gray-600">Loading QuickBooks Customers...</p>
      </div>
    );

  return (
    <div className="p-8 bg-gradient-to-br from-green-50 via-white to-emerald-50 min-h-screen">
      <h2 className="text-3xl font-bold text-gray-800 mb-6">
        QuickBooks Customers
      </h2>

      {customers.length === 0 ? (
        <p className="text-gray-600 text-lg">No customers found in QuickBooks.</p>
      ) : (
        <table className="w-full border border-gray-200 rounded-lg shadow-lg">
          <thead className="bg-green-600 text-white">
            <tr>
              <th className="p-3 text-left">Name</th>
              <th className="p-3 text-left">Email</th>
              <th className="p-3 text-left">Phone</th>
              <th className="p-3 text-left">Balance</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c, i) => (
              <tr key={i} className="odd:bg-white even:bg-green-50">
                <td className="p-3">{safeValue(c.DisplayName)}</td>
                <td className="p-3">{safeValue(c.PrimaryEmail)}</td>
                <td className="p-3">{safeValue(c.PrimaryPhone)}</td>
                <td className="p-3">${safeValue(c.Balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
