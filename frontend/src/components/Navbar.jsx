import React from "react";
import { useAuth } from "../context/AuthContext";
import { LogOut, Sparkles } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-50 w-full">
      {/* Top Gradient Accent */}
      <div className="h-[3px] w-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 animate-gradient-x"></div>

      {/* Glass Navbar */}
      <div className="bg-white/50 backdrop-blur-2xl border-b border-white/20 shadow-[0_8px_30px_rgba(0,0,0,0.05)]">
        <div className="max-w-7xl mx-auto h-20 flex items-center justify-between px-6 sm:px-10">
          {/* Brand */}
          <div className="flex items-center gap-3 group">
            <div className="relative flex items-center justify-center h-14 w-14 rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 p-[2px] shadow-lg transition-all duration-300 group-hover:shadow-indigo-400/50">
              <div className="bg-white h-full w-full rounded-2xl flex items-center justify-center">
                <img
                  src="/logo.svg"
                  alt="TaxMind AI Logo"
                  className="h-9 w-9 object-contain transition-transform duration-300 group-hover:scale-110"
                />
              </div>
            </div>
            <div>
              <h1 className="text-2xl font-extrabold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 bg-clip-text text-transparent tracking-tight flex items-center gap-1">
                TaxMind AI
                <Sparkles className="h-5 w-5 text-purple-500 animate-pulse" />
              </h1>
              <p className="text-xs text-gray-500 font-medium">
                Welcome to <span className="text-indigo-500 font-semibold">TaxMate</span> — meet{" "}
                <span className="text-purple-600 font-semibold">Max 👋</span>
              </p>
            </div>
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-5">
            {user && (
              <div className="hidden sm:flex items-center gap-3 pr-2">
                {/* Avatar */}
                <div className="relative group">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold shadow-md transition-transform duration-300 group-hover:scale-110">
                    {user.name ? user.name.charAt(0).toUpperCase() : "U"}
                  </div>
                  <span className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></span>
                </div>

                {/* Greeting */}
                <span className="text-sm text-gray-700 font-medium transition-all duration-300 hover:text-indigo-600">
                  Hello,{" "}
                  <span className="font-semibold capitalize text-purple-600">
                    {user.name || "User"}
                  </span>{" "}
                  👋
                </span>
              </div>
            )}

            {/* Logout Button */}
            <button
              onClick={logout}
              className="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl 
                bg-gradient-to-r from-red-500 to-rose-600 text-white shadow-md hover:shadow-lg 
                hover:from-red-600 hover:to-rose-700 active:scale-95 transition-all duration-300"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
