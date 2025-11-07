import React, { useState, useEffect } from "react";
import axios from "axios";
import { CreditCardIcon, BoltIcon, ShieldCheckIcon } from "@heroicons/react/24/solid";
import Lottie from "lottie-react";

export default function JoinTaxMate() {
  const [accounts, setAccounts] = useState(0);
  const [quickbooks, setQuickbooks] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [successAnimation, setSuccessAnimation] = useState(null);

  // ✅ Load success.json from /public dynamically
  useEffect(() => {
    fetch("/success.json")
      .then((res) => res.json())
      .then((data) => setSuccessAnimation(data))
      .catch((err) => console.error("Error loading success.json:", err));
  }, []);

  // ✅ FIXED: Real Stripe redirect logic
  const handleSubscribe = async () => {
    try {
      setLoading(true);
      const res = await axios.post("http://localhost:8000/create-checkout-session", {
        additional_accounts: accounts,
        quickbooks,
      });

      // ✅ Redirect user to Stripe Checkout page
      if (res.data && res.data.url) {
        window.location.href = res.data.url;
      } else {
        alert("❌ Stripe checkout URL not returned. Please check backend logs.");
        console.error("Stripe Response:", res.data);
      }
    } catch (err) {
      console.error("❌ Error creating checkout session:", err);
      alert("❌ Error creating checkout session. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (showSuccess) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-100 text-center p-6">
        <div className="max-w-lg bg-white rounded-3xl shadow-2xl p-10 border border-gray-100">
          {successAnimation && (
            <Lottie animationData={successAnimation} loop={false} className="h-64 mx-auto" />
          )}
          <h1 className="text-4xl font-extrabold text-purple-700 mt-4 mb-2">
            Subscription Successful! 🎉
          </h1>
          <p className="text-gray-600 mb-6">
            You’ve successfully joined <b>TaxMate</b> — Max is ready to help you maximize your refund.
          </p>
          <button
            onClick={() => setShowSuccess(false)}
            className="px-8 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-full font-semibold shadow hover:scale-105 transition"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-100 py-16 px-6">
      {/* Header Title */}
      <div className="text-center mb-12 animate-fadeIn">
        <h1 className="text-5xl font-extrabold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent drop-shadow-md">
          Join <span className="text-purple-700">TaxMate</span> 💼
        </h1>
        <p className="mt-4 text-gray-600 max-w-xl mx-auto text-lg leading-relaxed">
          Subscribe to your AI Tax Agent — <b>Max</b> — for just{" "}
          <span className="text-blue-600 font-semibold">$10/month</span>.
          <br />
          Add more accounts or enable QuickBooks integration anytime.
        </p>
      </div>

      {/* Card */}
      <div className="relative w-full max-w-lg bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl border border-gray-100 p-10 transition-all duration-300 hover:shadow-3xl hover:scale-[1.02]">
        {/* Glow effect */}
        <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-purple-100 via-white to-blue-100 opacity-70 blur-xl -z-10"></div>

        {/* Icon */}
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full shadow-lg">
            <CreditCardIcon className="h-10 w-10 text-white" />
          </div>
        </div>

        {/* Plan Details */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-800">Your Subscription Plan</h2>
          <p className="text-gray-500 mt-2">Simple, transparent pricing — no hidden fees.</p>
        </div>

        {/* Options */}
        <div className="space-y-5 mb-8">
          <div className="flex justify-between items-center border-b border-gray-200 pb-3">
            <span className="font-medium text-gray-700">
              Base Plan (includes 1 Account)
            </span>
            <span className="font-semibold text-blue-600">$10/month</span>
          </div>

          <div className="flex justify-between items-center border-b border-gray-200 pb-3">
            <span className="font-medium text-gray-700">
              Additional Accounts ($5 each)
            </span>
            <input
              type="number"
              min="0"
              value={accounts}
              onChange={(e) => setAccounts(parseInt(e.target.value) || 0)}
              className="w-20 border border-gray-300 rounded-lg p-2 text-center focus:ring-2 focus:ring-purple-400 focus:outline-none"
            />
          </div>

          <div className="flex justify-between items-center">
            <span className="font-medium text-gray-700">
              QuickBooks Add-on ($2/month)
            </span>
            <label className="inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={quickbooks}
                onChange={(e) => setQuickbooks(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-purple-400 rounded-full peer dark:bg-gray-300 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600 relative"></div>
            </label>
          </div>
        </div>

        {/* Total Price */}
        <div className="text-center mb-6 bg-gradient-to-r from-purple-50 to-blue-50 p-4 rounded-xl shadow-inner">
          <p className="text-gray-600 font-medium">Estimated Monthly Total</p>
          <p className="text-3xl font-extrabold text-purple-700 mt-1">
            ${10 + accounts * 5 + (quickbooks ? 2 : 0)}
            <span className="text-base text-gray-500"> / month</span>
          </p>
        </div>

        {/* Button */}
        <button
          onClick={handleSubscribe}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold py-3 rounded-full shadow-lg hover:from-purple-700 hover:to-blue-700 transition-all duration-300 hover:scale-[1.02] active:scale-95 disabled:opacity-60"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <BoltIcon className="animate-spin h-5 w-5 text-yellow-300" />
              Processing...
            </span>
          ) : (
            <>
              <BoltIcon className="h-5 w-5 text-yellow-300" />
              Join TaxMate Now 🚀
            </>
          )}
        </button>

        {/* Guarantee */}
        <div className="text-center mt-6">
          <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
            <ShieldCheckIcon className="h-5 w-5 text-green-500" />
            Secure payment powered by <span className="font-semibold text-gray-700">Stripe</span> 🔒
          </div>
          <p className="text-sm text-gray-400 mt-1">Cancel anytime. Satisfaction guaranteed.</p>
        </div>

        {/* Compare Plans Section */}
        <div className="mt-8 border-t border-gray-200 pt-4">
          <button
            onClick={() => setShowCompare(!showCompare)}
            className="text-purple-700 font-semibold text-sm hover:underline"
          >
            {showCompare ? "Hide Plan Comparison ▲" : "Compare Plans ▼"}
          </button>

          {showCompare && (
            <div className="mt-4 bg-gradient-to-br from-blue-50 via-white to-purple-50 rounded-xl p-4 shadow-inner text-sm text-gray-700 animate-fadeIn">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr>
                    <th className="p-2 font-semibold">Feature</th>
                    <th className="p-2 font-semibold">Basic</th>
                    <th className="p-2 font-semibold">Pro</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="p-2">AI Tax Agent (Max)</td>
                    <td className="p-2 text-green-600">✔</td>
                    <td className="p-2 text-green-600">✔</td>
                  </tr>
                  <tr>
                    <td className="p-2">Receipt & Mileage Tracking</td>
                    <td className="p-2 text-green-600">✔</td>
                    <td className="p-2 text-green-600">✔</td>
                  </tr>
                  <tr>
                    <td className="p-2">QuickBooks Integration</td>
                    <td className="p-2 text-gray-400">✖</td>
                    <td className="p-2 text-green-600">✔</td>
                  </tr>
                  <tr>
                    <td className="p-2">Multiple Accounts</td>
                    <td className="p-2 text-gray-400">✖</td>
                    <td className="p-2 text-green-600">✔</td>
                  </tr>
                  <tr>
                    <td className="p-2">Priority Support</td>
                    <td className="p-2 text-gray-400">✖</td>
                    <td className="p-2 text-green-600">✔</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
