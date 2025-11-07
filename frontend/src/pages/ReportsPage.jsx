import React, { useEffect, useState } from "react";
import jsPDF from "jspdf";
import {
  DocumentArrowDownIcon,
  EnvelopeIcon,
} from "@heroicons/react/24/solid";
import {
  PieChart,
  Pie,
  Tooltip,
  Cell,
  ResponsiveContainer,
  Legend,
} from "recharts";

export default function ReportsPage() {
  const [summary, setSummary] = useState({});
  const COLORS = ["#6366F1", "#10B981", "#F59E0B", "#EC4899"];

  useEffect(() => {
    fetch("http://127.0.0.1:8000/reports-summary")
      .then((res) => res.json())
      .then((data) => setSummary(data.summary || {}))
      .catch(() => {});
  }, []);

  const downloadPDF = () => {
    const doc = new jsPDF();
    doc.text("Expense Summary", 20, 20);
    Object.entries(summary).forEach(([key, val], i) =>
      doc.text(`${key}: $${val.toFixed(2)}`, 20, 40 + i * 10)
    );
    doc.save("Expense_Summary.pdf");
  };

  const emailReport = () => {
    const subject = encodeURIComponent("Your Expense Summary");
    const body = encodeURIComponent(
      Object.entries(summary)
        .map(([k, v]) => `${k}: $${v.toFixed(2)}`)
        .join("\n")
    );
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  };

  const data = Object.entries(summary).map(([key, value]) => ({
    name: key,
    value,
  }));

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-8">
      <div className="text-center mb-10">
        <h2 className="text-4xl font-extrabold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          Reports Center
        </h2>
        <p className="text-gray-600">
          AI-powered insights from your receipts and mileage.
        </p>
      </div>

      <div className="bg-white rounded-2xl p-8 shadow-md mb-10">
        <h3 className="text-2xl font-semibold text-gray-800 mb-4">
          Expense Breakdown
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              dataKey="value"
              data={data}
              cx="50%"
              cy="50%"
              outerRadius={100}
              label
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-col sm:flex-row justify-center gap-4">
        <button
          onClick={downloadPDF}
          className="flex items-center justify-center gap-2 px-5 py-3 rounded-lg text-white font-medium bg-gradient-to-r from-blue-500 to-purple-600 hover:scale-105 transition"
        >
          <DocumentArrowDownIcon className="h-5 w-5" />
          Download PDF
        </button>
        <button
          onClick={emailReport}
          className="flex items-center justify-center gap-2 px-5 py-3 rounded-lg text-white font-medium bg-gradient-to-r from-green-500 to-teal-600 hover:scale-105 transition"
        >
          <EnvelopeIcon className="h-5 w-5" />
          Email to Accountant
        </button>
      </div>
    </div>
  );
}
