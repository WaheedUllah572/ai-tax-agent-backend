import React, { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import {
  HomeIcon,
  ChatBubbleLeftRightIcon,
  DocumentArrowUpIcon,
  MapIcon,
  ChartBarIcon,
  ArrowRightOnRectangleIcon,
  UserPlusIcon,
  CreditCardIcon,
  CheckCircleIcon,
  XCircleIcon,
  BanknotesIcon,
} from "@heroicons/react/24/outline";

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [userName, setUserName] = useState("User");
  const [qbConnected, setQbConnected] = useState(false);

  // ✅ Final, guaranteed working Base URL
  const baseUrl =
    import.meta?.env?.VITE_API_BASE_URL?.trim() ||
    process.env.REACT_APP_API_BASE_URL?.trim() ||
    "https://ai-tax-agent-backend-klwl.onrender.com";

  console.log("✅ Loaded Base URL:", baseUrl);

  // ✅ Load stored username
  useEffect(() => {
    const storedUser = JSON.parse(localStorage.getItem("user"));
    if (storedUser?.name) setUserName(storedUser.name);
    else if (storedUser?.username) setUserName(storedUser.username);
  }, []);

  // ✅ Check QuickBooks connection
  useEffect(() => {
    const checkQuickBooksStatus = async () => {
      try {
        const res = await axios.get(`${baseUrl}/quickbooks/status`, {
          headers: { "Cache-Control": "no-cache" },
          withCredentials: true,
        });
        const connected =
          res.data?.connected === true ||
          res.data?.status?.includes("Connected") ||
          false;
        setQbConnected(connected);
      } catch (err) {
        console.error("QuickBooks status check failed:", err.message);
        setQbConnected(false);
      }
    };

    checkQuickBooksStatus();
    const interval = setInterval(checkQuickBooksStatus, 15000);
    window.addEventListener("qb-status-updated", checkQuickBooksStatus);

    return () => {
      clearInterval(interval);
      window.removeEventListener("qb-status-updated", checkQuickBooksStatus);
    };
  }, [baseUrl]);

  const handleLogout = () => {
    localStorage.removeItem("user");
    navigate("/login");
  };

  const menuItems = [
    { name: "Dashboard", path: "/dashboard", icon: <HomeIcon className="h-5 w-5" /> },
    { name: "Chatbot", path: "/chatbot", icon: <ChatBubbleLeftRightIcon className="h-5 w-5" /> },
    { name: "Receipts", path: "/receipts", icon: <DocumentArrowUpIcon className="h-5 w-5" /> },
    { name: "Mileage", path: "/mileage", icon: <MapIcon className="h-5 w-5" /> },
    { name: "Reports", path: "/reports", icon: <ChartBarIcon className="h-5 w-5" /> },
  ];

  const subscriptionItems = [
    { name: "Join TaxMate", path: "/join", icon: <CreditCardIcon className="h-5 w-5" /> },
    {
      name: "Subscription Success",
      path: "/subscription-success",
      icon: <CheckCircleIcon className="h-5 w-5 text-green-600" />,
    },
    {
      name: "Subscription Cancel",
      path: "/subscription-cancel",
      icon: <XCircleIcon className="h-5 w-5 text-red-500" />,
    },
  ];

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-gradient-to-b from-indigo-100 to-white border-r border-gray-200 flex flex-col justify-between">
        <div>
          {/* Logo + Title */}
          <div className="flex items-center justify-center py-6 border-b border-gray-200">
            <img
              src="/logo.svg"
              alt="TaxMind AI"
              className="h-10 w-10 mr-2 rounded-full bg-white shadow"
            />
            <h1 className="text-xl font-bold text-indigo-700">TaxMind AI</h1>
          </div>

          {/* Main Nav */}
          <nav className="p-4 space-y-2">
            {menuItems.map((item) => (
              <Link
                key={item.name}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-2 rounded-lg font-medium transition ${
                  location.pathname === item.path
                    ? "bg-indigo-600 text-white shadow-md"
                    : "text-gray-700 hover:bg-indigo-100"
                }`}
              >
                {item.icon}
                {item.name}
              </Link>
            ))}
          </nav>

          {/* Subscription Section */}
          <div className="border-t border-gray-200 mt-4 pt-4">
            <h4 className="text-xs font-semibold text-gray-500 uppercase px-4 mb-2">
              Subscription
            </h4>
            <nav className="p-2 space-y-2">
              {subscriptionItems.map((item) => (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-2 rounded-lg font-medium transition ${
                    location.pathname === item.path
                      ? "bg-indigo-600 text-white shadow-md"
                      : "text-gray-700 hover:bg-indigo-100"
                  }`}
                >
                  {item.icon}
                  {item.name}
                </Link>
              ))}
            </nav>
          </div>

          {/* QuickBooks Connection Status */}
          <div className="mx-4 mt-3 mb-2 flex items-center justify-between bg-white border border-gray-200 rounded-xl shadow-sm px-3 py-2 transition-all duration-300">
            <div className="flex items-center gap-2">
              <BanknotesIcon className="h-5 w-5 text-green-600" />
              <span className="font-medium text-sm text-gray-700">
                QuickBooks
              </span>
            </div>
            <span
              className={`text-sm font-semibold ${
                qbConnected ? "text-green-600" : "text-red-500"
              }`}
            >
              {qbConnected ? "🟢 Connected" : "🔴 Not Connected"}
            </span>
          </div>
        </div>

        {/* Footer Links (Login/Register) */}
        <div className="p-4 border-t border-gray-200">
          <Link
            to="/login"
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition"
          >
            <ArrowRightOnRectangleIcon className="h-5 w-5" />
            Login
          </Link>
          <Link
            to="/register"
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition"
          >
            <UserPlusIcon className="h-5 w-5" />
            Register
          </Link>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="flex justify-between items-center bg-white border-b border-gray-200 px-6 py-4 shadow-sm sticky top-0 z-10">
          <h2 className="text-xl font-semibold text-gray-700">
            Welcome to TaxMate — meet{" "}
            <span className="text-indigo-600">Max</span> 👋
          </h2>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">Hello, {userName} 👋</span>
            <button
              onClick={handleLogout}
              className="bg-red-500 text-white px-4 py-1.5 text-sm rounded-full hover:bg-red-600 transition"
            >
              Logout
            </button>
          </div>
        </header>

        {/* ✅ Fixed Main Wrapper */}
        <main className="flex-1 overflow-y-auto min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
