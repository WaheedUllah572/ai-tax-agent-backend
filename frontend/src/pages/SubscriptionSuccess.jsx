import React from "react";

export default function SubscriptionSuccess() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center bg-gradient-to-br from-green-50 via-white to-green-100 p-6">
      <div className="max-w-lg bg-white rounded-3xl shadow-2xl p-10 border border-green-200">
        <h1 className="text-4xl font-extrabold text-green-600 mb-4">
          ✅ Subscription Successful!
        </h1>
        <p className="text-gray-700 text-lg mb-6">
          Welcome to <span className="font-bold text-green-700">TaxMate</span> 🎉<br />
          Your AI Tax Agent <b>Max</b> is now active and ready to assist you.
        </p>

        <a
          href="/dashboard"
          className="px-8 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white text-lg rounded-full shadow-lg hover:scale-105 transition"
        >
          Go to Dashboard →
        </a>
      </div>
    </div>
  );
}
