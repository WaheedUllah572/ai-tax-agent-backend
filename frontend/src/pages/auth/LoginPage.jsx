import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { UserIcon, LockClosedIcon } from "@heroicons/react/24/solid";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();

    // ✅ Simple mock login for now
    const user = {
      name: email.split("@")[0], // Extract name from email
      email,
    };

    // Save user to localStorage so Layout can access it
    localStorage.setItem("user", JSON.stringify(user));

    // Optional: call backend login (if implemented)
    login(email, password);

    // Redirect to dashboard
    navigate("/dashboard");
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-purple-200 via-pink-100 to-blue-200">
      {/* Welcome Section */}
      <div className="text-center mb-10 animate-fadeIn">
        <img
          src="/logo.svg"
          alt="TaxMind AI Logo"
          className="mx-auto h-32 w-32 mb-6 rounded-full bg-white object-contain p-2 pt-1 drop-shadow-2xl"
        />
        <h1 className="text-5xl md:text-6xl font-extrabold text-gray-800 drop-shadow-lg">
          Welcome to <span className="text-purple-600">TaxMind AI</span>
        </h1>
        <p className="mt-4 text-gray-600 max-w-xl mx-auto text-base md:text-lg">
          🚀 Manage your taxes smarter, faster, and stress-free. Upload receipts, track mileage, and let AI handle the rest.
        </p>
      </div>

      {/* Login Card */}
      <div className="w-full max-w-md bg-white/80 backdrop-blur-lg p-8 rounded-3xl shadow-2xl border border-gray-200">
        <div className="flex justify-center mb-4">
          <img
            src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
            alt="User Avatar"
            className="w-20 h-20 rounded-full border-4 border-purple-300 shadow-md"
          />
        </div>

        <h2 className="text-2xl font-bold text-center text-gray-800 mb-4">
          Sign in to Continue 👋
        </h2>

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="relative">
            <UserIcon className="absolute left-3 top-3.5 h-5 w-5 text-gray-400" />
            <input
              type="email"
              placeholder="Email Address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition"
              required
            />
          </div>

          <div className="relative">
            <LockClosedIcon className="absolute left-3 top-3.5 h-5 w-5 text-gray-400" />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-gradient-to-r from-purple-500 to-blue-500 text-white py-3 rounded-xl font-semibold shadow-md hover:shadow-lg transition transform hover:-translate-y-0.5"
          >
            🔑 Login
          </button>
        </form>

        <p className="text-sm text-center text-gray-600 mt-6">
          Don’t have an account?{" "}
          <Link to="/register" className="text-purple-600 font-semibold hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
