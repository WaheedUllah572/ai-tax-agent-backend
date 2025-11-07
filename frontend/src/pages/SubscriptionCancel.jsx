import React from "react";

export default function SubscriptionCancel() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center bg-gradient-to-br from-red-50 via-white to-red-100 p-6">
      <div className="max-w-lg bg-white rounded-3xl shadow-2xl p-10 border border-red-200">
        <h1 className="text-4xl font-extrabold text-red-600 mb-4">
          ❌ Subscription Cancelled
        </h1>
        <p className="text-gray-700 text-lg mb-6">
          No problem! You can join <span className="font-bold text-red-700">TaxMate</span> anytime
          to start maximizing your refund.
        </p>

        <a
          href="/join"
          className="px-8 py-3 bg-gradient-to-r from-red-500 to-pink-500 text-white text-lg rounded-full shadow-lg hover:scale-105 transition"
        >
          Try Again →
        </a>
      </div>
    </div>
  );
}
