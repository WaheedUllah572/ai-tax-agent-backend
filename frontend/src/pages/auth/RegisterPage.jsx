import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { UserIcon, EnvelopeIcon, LockClosedIcon } from "@heroicons/react/24/solid";

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleRegister = (e) => {
    e.preventDefault();

    if (!name || !email || !password) {
      alert("⚠️ All fields are required.");
      return;
    }
    if (password !== confirmPassword) {
      alert("⚠️ Passwords do not match.");
      return;
    }

    // ✅ Save new user to localStorage
    const user = { name, email };
    localStorage.setItem("user", JSON.stringify(user));

    // Optional: call your backend or auth context
    register(name, email, password);

    // Redirect after register
    navigate("/dashboard");
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-green-200 via-white to-blue-200">
      <div className="text-center mb-8 animate-fadeIn">
        <img
          src="/logo.svg"
          alt="TaxMind AI Logo"
          className="mx-auto h-32 w-32 mb-6 rounded-full bg-white object-contain p-2 pt-1 drop-shadow-2xl"
        />
        <h1 className="text-5xl md:text-6xl font-extrabold text-gray-800 drop-shadow-lg">
          Create your <span className="text-green-600">TaxMind AI</span> Account ✨
        </h1>
        <p className="mt-3 text-gray-600 max-w-xl mx-auto text-lg">
          🚀 Sign up today to manage taxes smarter, track expenses, upload receipts, and get AI-powered tips.
        </p>
      </div>

      <div className="w-full max-w-md bg-white/80 backdrop-blur-lg p-8 rounded-3xl shadow-2xl border border-gray-200">
        <div className="flex justify-center mb-4">
          <img
            src="https://cdn-icons-png.flaticon.com/512/456/456212.png"
            alt="Register Avatar"
            className="w-20 h-20 rounded-full border-4 border-green-300 shadow-md"
          />
        </div>

        <h2 className="text-2xl font-bold text-center text-gray-800 mb-2">
          Join TaxMind AI 🚀
        </h2>

        <form onSubmit={handleRegister} className="space-y-4">
          <div className="relative">
            <UserIcon className="absolute left-3 top-3.5 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition"
              required
            />
          </div>

          <div className="relative">
            <EnvelopeIcon className="absolute left-3 top-3.5 h-5 w-5 text-gray-400" />
            <input
              type="email"
              placeholder="Email Address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition"
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
              className="w-full pl-10 pr-4 py-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition"
              required
            />
          </div>

          <div className="relative">
            <LockClosedIcon className="absolute left-3 top-3.5 h-5 w-5 text-gray-400" />
            <input
              type="password"
              placeholder="Confirm Password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-gradient-to-r from-green-500 to-blue-500 text-white py-3 rounded-xl font-semibold shadow-md hover:shadow-lg transition transform hover:-translate-y-0.5"
          >
            ✨ Register
          </button>
        </form>

        <p className="text-sm text-center text-gray-600 mt-6">
          Already have an account?{" "}
          <Link to="/login" className="text-green-600 font-semibold hover:underline">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}
