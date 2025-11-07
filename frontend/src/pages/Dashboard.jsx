import React, { useState, useEffect } from "react";
import {
  BuildingOfficeIcon,
  ClipboardDocumentCheckIcon,
  UserGroupIcon,
  BanknotesIcon,
  CurrencyDollarIcon,
} from "@heroicons/react/24/outline";
import { useNavigate } from "react-router-dom";
import GmailConnect from "../components/GmailConnect"; // ✅ Added import

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // ✅ Dynamic Base URL
  const baseUrl =
    process.env.REACT_APP_API_BASE_URL ||
    window?.__API_BASE_URL__ ||
    "https://ai-tax-agent-backend-klwl.onrender.com";

  console.log("🌐 QuickBooks Connect URL:", baseUrl);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 1200);
    return () => clearTimeout(timer);
  }, []);

  const handleConnectQuickBooks = () => {
    const popup = window.open(
      `${baseUrl}/quickbooks/connect`,
      "_blank",
      "noopener,noreferrer,width=600,height=800"
    );
    const timer = setInterval(() => {
      if (popup && popup.closed) {
        clearInterval(timer);
        window.dispatchEvent(new Event("qb-status-updated"));
      }
    }, 1000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-indigo-200 via-white to-purple-200">
        <div className="relative flex items-center justify-center">
          <div className="w-20 h-20 border-4 border-t-4 border-indigo-500 rounded-full animate-spin"></div>
          <div className="absolute w-10 h-10 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full animate-pulse shadow-2xl"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full min-h-screen bg-gradient-to-br from-indigo-100 via-white to-purple-100 p-8 overflow-y-auto">
      {/* Background blur gradients */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-purple-300 opacity-30 blur-[120px] rounded-full -z-10"></div>
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-blue-300 opacity-30 blur-[120px] rounded-full -z-10"></div>

      {/* HEADER */}
      <div className="flex flex-col items-center text-center mb-16">
        <img
          src="/logo.svg"
          alt="TaxMind AI Logo"
          className="h-32 w-32 md:h-40 md:w-40 mb-5 rounded-full bg-white/80 backdrop-blur-xl shadow-2xl border border-gray-100 p-2 hover:scale-105 transition-transform duration-500"
        />
        <h1 className="text-6xl font-extrabold bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 bg-clip-text text-transparent drop-shadow-lg tracking-tight">
          TaxMind AI
        </h1>
        <p className="text-gray-600 mt-3 text-lg max-w-2xl">
          Simplifying taxes with intelligence, design, and automation.
        </p>
      </div>

      {/* WELCOME SECTION */}
      <div className="text-center mb-12 animate-fadeIn">
        <h2 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 bg-clip-text text-transparent drop-shadow-sm">
          Welcome to{" "}
          <span className="text-purple-700 font-extrabold">TaxMate</span> — meet
          Max, your AI Tax Agent 👋
        </h2>
        <p className="text-gray-600 mt-3 text-lg max-w-2xl mx-auto leading-relaxed">
          Max helps you manage receipts, mileage, and reports — automatically.
          Streamline your financial workflow with AI-powered precision.
        </p>
      </div>

      {/* QUICKBOOKS CONNECT BUTTON */}
      <div className="text-center mb-12">
        <button
          onClick={handleConnectQuickBooks}
          className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 text-white font-semibold rounded-xl shadow-md hover:bg-green-700 transition-all duration-300 hover:scale-105"
        >
          <img
            src="https://cdn.iconscout.com/icon/free/png-256/free-quickbooks-282300.png"
            alt="QuickBooks Logo"
            className="h-6 w-6"
          />
          Connect QuickBooks
        </button>
      </div>

      {/* ✅ GMAIL CONNECT MODULE */}
      <section className="mt-10 flex justify-center">
        <div className="max-w-4xl w-full">
          <GmailConnect />
        </div>
      </section>

      {/* QUICKBOOKS DASHBOARD */}
      <div className="mt-16">
        <h2 className="text-3xl font-bold text-gray-800 text-center mb-8">
          QuickBooks Test Dashboard 🧾
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
          <button
            onClick={() => navigate("/quickbooks/companyinfo")}
            className="flex flex-col items-center justify-center bg-white border border-blue-200 p-6 rounded-2xl shadow-lg hover:bg-blue-50 hover:-translate-y-1 transition-all duration-300"
          >
            <BuildingOfficeIcon className="h-10 w-10 text-blue-600 mb-2" />
            <span className="font-semibold text-blue-700">Company Info</span>
          </button>

          <button
            onClick={() => navigate("/quickbooks/customers")}
            className="flex flex-col items-center justify-center bg-white border border-green-200 p-6 rounded-2xl shadow-lg hover:bg-green-50 hover:-translate-y-1 transition-all duration-300"
          >
            <UserGroupIcon className="h-10 w-10 text-green-600 mb-2" />
            <span className="font-semibold text-green-700">Customers</span>
          </button>

          <button
            onClick={() => navigate("/quickbooks/invoices")}
            className="flex flex-col items-center justify-center bg-white border border-indigo-200 p-6 rounded-2xl shadow-lg hover:bg-indigo-50 hover:-translate-y-1 transition-all duration-300"
          >
            <ClipboardDocumentCheckIcon className="h-10 w-10 text-indigo-600 mb-2" />
            <span className="font-semibold text-indigo-700">Invoices</span>
          </button>

          <button
            onClick={() => navigate("/quickbooks/accounts")}
            className="flex flex-col items-center justify-center bg-white border border-yellow-200 p-6 rounded-2xl shadow-lg hover:bg-yellow-50 hover:-translate-y-1 transition-all duration-300"
          >
            <BanknotesIcon className="h-10 w-10 text-yellow-600 mb-2" />
            <span className="font-semibold text-yellow-700">Accounts</span>
          </button>

          <button
            onClick={() => navigate("/quickbooks/expenses")}
            className="flex flex-col items-center justify-center bg-white border border-purple-200 p-6 rounded-2xl shadow-lg hover:bg-purple-50 hover:-translate-y-1 transition-all duration-300"
          >
            <CurrencyDollarIcon className="h-10 w-10 text-purple-600 mb-2" />
            <span className="font-semibold text-purple-700">Add Expense</span>
          </button>
        </div>
      </div>

      {/* FOOTER */}
      <footer className="mt-20 text-center text-gray-500 text-sm">
        © {new Date().getFullYear()}{" "}
        <span className="font-semibold text-indigo-600">TaxMind AI</span> — Powered by Smart Finance Intelligence ⚡
      </footer>
    </div>
  );
}
