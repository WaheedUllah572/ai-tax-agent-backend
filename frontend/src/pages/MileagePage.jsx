import React, { useState } from "react";
import axios from "axios";
import { PlusIcon, TrashIcon, ChartBarIcon, MapIcon } from "@heroicons/react/24/solid";

export default function MileagePage() {
  const [trips, setTrips] = useState([]);
  const [form, setForm] = useState({
    date: "",
    start: "",
    destination: "",
    purpose: "",
    miles: "",
    method: "",
  });
  const [loadingMiles, setLoadingMiles] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  // ✅ Call FastAPI backend
  const calculateMiles = async () => {
    if (!form.start || !form.destination) {
      alert("⚠️ Please enter both Start Location and Destination.");
      return;
    }

    try {
      setLoadingMiles(true);
      const res = await axios.get("http://localhost:8000/calculate-miles", {
        params: { start: form.start, destination: form.destination },
      });

      if (res.data.error) {
        alert("❌ " + res.data.error);
      } else {
        setForm({ ...form, miles: res.data.miles, method: res.data.method });
      }
    } catch (error) {
      console.error("Error calculating miles:", error);
      alert("❌ Error calculating miles. Please try again.");
    } finally {
      setLoadingMiles(false);
    }
  };

  const addTrip = () => {
    if (!form.date || !form.start || !form.destination || !form.miles) {
      alert("⚠️ Please fill in all required fields and calculate miles first.");
      return;
    }
    const newTrip = {
      id: Date.now(),
      ...form,
      miles: parseFloat(form.miles),
    };
    setTrips([...trips, newTrip]);
    setForm({ date: "", start: "", destination: "", purpose: "", miles: "", method: "" });
  };

  const deleteTrip = (id) => {
    setTrips(trips.filter((t) => t.id !== id));
  };

  // Analytics
  const totalMiles = trips.reduce((sum, t) => sum + t.miles, 0);
  const avgMiles = trips.length > 0 ? (totalMiles / trips.length).toFixed(2) : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-8 rounded-2xl shadow-lg">
      {/* Page Header */}
      <div className="mb-10 text-center flex flex-col items-center justify-center">
        <img
          src="/mileage-logo.png" // ✅ your logo file in public folder
          alt="Mileage Tracker Logo"
          className="h-32 w-32 mb-6 drop-shadow-2xl transform hover:scale-105 transition duration-300"
        />
        <h2 className="text-5xl font-extrabold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent drop-shadow-lg">
          Mileage Tracker
        </h2>
        <p className="text-gray-600 mt-3 text-lg">
          Log, organize, and analyze your trips with AI-powered mileage insights.
        </p>
      </div>

      {/* Add Trip Form */}
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-8 border border-gray-100">
        <h3 className="flex items-center gap-2 text-xl font-semibold text-gray-800 mb-4">
          <PlusIcon className="h-6 w-6 text-purple-600" /> Add New Trip
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <input
            type="date"
            name="date"
            value={form.date}
            onChange={handleChange}
            className="border rounded-xl px-3 py-2 shadow-sm focus:ring-2 focus:ring-purple-500 outline-none"
          />
          <input
            type="text"
            name="start"
            placeholder="Start Location"
            value={form.start}
            onChange={handleChange}
            className="border rounded-xl px-3 py-2 shadow-sm focus:ring-2 focus:ring-purple-500 outline-none"
          />
          <input
            type="text"
            name="destination"
            placeholder="Destination"
            value={form.destination}
            onChange={handleChange}
            className="border rounded-xl px-3 py-2 shadow-sm focus:ring-2 focus:ring-purple-500 outline-none"
          />
          <input
            type="text"
            name="purpose"
            placeholder="Purpose"
            value={form.purpose}
            onChange={handleChange}
            className="border rounded-xl px-3 py-2 shadow-sm focus:ring-2 focus:ring-purple-500 outline-none"
          />
          <input
            type="text"
            name="miles"
            placeholder="Miles"
            value={form.miles ? `${form.miles} (${form.method})` : ""}
            readOnly
            className="border rounded-xl px-3 py-2 shadow-sm bg-gray-100 cursor-not-allowed"
          />
        </div>

        {/* Buttons */}
        <div className="flex gap-4 mt-4">
          <button
            onClick={calculateMiles}
            disabled={loadingMiles}
            className="px-6 py-2 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl shadow-md hover:from-green-600 hover:to-emerald-700 transition disabled:opacity-50 flex items-center gap-2"
          >
            <MapIcon className="h-5 w-5" />
            {loadingMiles ? "Calculating..." : "Calculate Miles"}
          </button>

          <button
            onClick={addTrip}
            disabled={loadingMiles}
            className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl shadow-md hover:from-blue-600 hover:to-purple-700 transition disabled:opacity-50 flex items-center gap-2"
          >
            <PlusIcon className="h-5 w-5" /> Add Trip
          </button>
        </div>
      </div>

      {/* Analytics Panel */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-2xl shadow-md border">
          <h4 className="text-gray-500 text-sm">Total Trips</h4>
          <p className="text-2xl font-bold text-blue-600">{trips.length}</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-md border">
          <h4 className="text-gray-500 text-sm">Total Miles</h4>
          <p className="text-2xl font-bold text-purple-600">{totalMiles}</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-md border">
          <h4 className="text-gray-500 text-sm">Average Miles</h4>
          <p className="text-2xl font-bold text-green-600">{avgMiles}</p>
        </div>
      </div>

      {/* Trips Table */}
      <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
        <h3 className="flex items-center gap-2 text-xl font-semibold text-gray-800 mb-4">
          <ChartBarIcon className="h-6 w-6 text-blue-600" /> Trip Log
        </h3>
        {trips.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gradient-to-r from-blue-50 to-purple-50">
                <tr>
                  <th className="px-6 py-3 text-left font-semibold text-gray-700">Date</th>
                  <th className="px-6 py-3 text-left font-semibold text-gray-700">Start</th>
                  <th className="px-6 py-3 text-left font-semibold text-gray-700">Destination</th>
                  <th className="px-6 py-3 text-left font-semibold text-gray-700">Purpose</th>
                  <th className="px-6 py-3 text-left font-semibold text-gray-700">Miles</th>
                  <th className="px-6 py-3 text-left font-semibold text-gray-700">Method</th>
                  <th className="px-6 py-3 text-center font-semibold text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {trips.map((trip) => (
                  <tr key={trip.id} className="hover:bg-gray-50">
                    <td className="px-6 py-3 text-gray-800">{trip.date}</td>
                    <td className="px-6 py-3 text-gray-600">{trip.start}</td>
                    <td className="px-6 py-3 text-gray-600">{trip.destination}</td>
                    <td className="px-6 py-3 text-gray-600">{trip.purpose}</td>
                    <td className="px-6 py-3 text-gray-600">{trip.miles}</td>
                    <td className="px-6 py-3 text-gray-600">{trip.method}</td>
                    <td className="px-6 py-3 text-center">
                      <button
                        onClick={() => deleteTrip(trip.id)}
                        className="flex items-center gap-1 text-red-600 hover:text-red-800 font-medium"
                      >
                        <TrashIcon className="h-4 w-4" /> Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center">No trips logged yet.</p>
        )}
      </div>
    </div>
  );
}
