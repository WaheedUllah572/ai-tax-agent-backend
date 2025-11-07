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

export default function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  const BASE_URL =
    process.env.REACT_APP_API_BASE_URL?.trim() ||
    window?.__API_BASE_URL__?.trim() ||
    "https://symbols-superb-icons-exhibitions.trycloudflare.com";

  useEffect(() => {
    axios
      .get(`${BASE_URL}/quickbooks/invoices`)
      .then((res) => setInvoices(res.data.invoices || []))
      .catch((err) => {
        console.error("Error fetching invoices:", err.message);
        setInvoices([]);
      })
      .finally(() => setLoading(false));
  }, [BASE_URL]);

  if (loading)
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
        <p className="text-lg text-gray-600">Loading QuickBooks Invoices...</p>
      </div>
    );

  return (
    <div className="p-8 bg-gradient-to-br from-indigo-50 via-white to-purple-50 min-h-screen">
      <h2 className="text-3xl font-bold text-gray-800 mb-6">
        QuickBooks Invoices
      </h2>

      {invoices.length === 0 ? (
        <p className="text-gray-600 text-lg">No invoices found in QuickBooks.</p>
      ) : (
        <table className="w-full border border-gray-200 rounded-lg shadow-lg">
          <thead className="bg-indigo-600 text-white">
            <tr>
              <th className="p-3 text-left">Invoice #</th>
              <th className="p-3 text-left">Customer</th>
              <th className="p-3 text-left">Total</th>
              <th className="p-3 text-left">Due Date</th>
              <th className="p-3 text-left">Balance</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv, i) => (
              <tr key={i} className="odd:bg-white even:bg-indigo-50">
                <td className="p-3">{safeValue(inv.InvoiceNumber)}</td>
                <td className="p-3">{safeValue(inv.CustomerName)}</td>
                <td className="p-3">${safeValue(inv.TotalAmt)}</td>
                <td className="p-3">{safeValue(inv.DueDate)}</td>
                <td className="p-3">${safeValue(inv.Balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
