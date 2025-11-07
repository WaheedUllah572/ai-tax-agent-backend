import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  HomeIcon,
  ChatBubbleLeftRightIcon,
  DocumentArrowUpIcon,
  MapIcon,
  ChartBarIcon,
  BanknotesIcon,
} from "@heroicons/react/24/outline";
import axios from "axios";

// ✅ Use CRA-style env variable
const BASE_URL =
  process.env.REACT_APP_API_BASE_URL?.trim() ||
  "http://localhost:8000";

const navItems = [
  { name: "Dashboard", path: "/", icon: <HomeIcon className="h-5 w-5" /> },
  { name: "Chatbot", path: "/chatbot", icon: <ChatBubbleLeftRightIcon className="h-5 w-5" /> },
  { name: "Receipts", path: "/receipts", icon: <DocumentArrowUpIcon className="h-5 w-5" /> },
  { name: "Mileage", path: "/mileage", icon: <MapIcon className="h-5 w-5" /> },
  { name: "Reports", path: "/reports", icon: <ChartBarIcon className="h-5 w-5" /> },
];

export default function Sidebar() {
  const { pathname } = useLocation();
  const [qbConnected, setQbConnected] = useState(false);

  useEffect(() => {
    const checkQuickBooksStatus = async () => {
      try {
        const res = await axios.get(`${BASE_URL}/quickbooks/status`);
        setQbConnected(res.data?.connected === true);
      } catch {
        setQbConnected(false);
      }
    };
    checkQuickBooksStatus();
    const interval = setInterval(checkQuickBooksStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <aside className="w-64 bg-gradient-to-b from-blue-50 via-white to-purple-50 shadow-xl hidden md:flex flex-col rounded-r-2xl">
      <div className="h-28 flex items-center justify-center gap-3 border-b">
        <div className="flex items-center justify-center h-16 w-16 rounded-full bg-white shadow-md overflow-hidden">
          <img src="/logo.svg" alt="TaxMind AI Logo" className="h-full w-full object-contain p-2 pt-1" />
        </div>
        <span className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 drop-shadow-md">
          TaxMind AI
        </span>
      </div>

      <div className="mx-4 mt-3 mb-1 flex items-center justify-between bg-white border border-gray-200 rounded-xl shadow-sm px-3 py-2">
        <div className="flex items-center gap-2">
          <BanknotesIcon className="h-5 w-5 text-green-600" />
          <span className="font-medium text-sm text-gray-700">QuickBooks</span>
        </div>
        <span className={`text-sm font-semibold ${qbConnected ? "text-green-600" : "text-red-500"}`}>
          {qbConnected ? "🟢 Connected" : "🔴 Not Connected"}
        </span>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.name}
            to={item.path}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition ${
              pathname === item.path
                ? "bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg"
                : "text-gray-700 hover:bg-gradient-to-r hover:from-blue-100 hover:to-purple-100 hover:text-blue-600"
            }`}
          >
            {item.icon}
            {item.name}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
