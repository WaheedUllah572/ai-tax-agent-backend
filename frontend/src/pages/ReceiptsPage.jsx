import React, { useState, useRef } from "react";
import { CloudArrowUpIcon, CameraIcon } from "@heroicons/react/24/outline";

export default function ReceiptsPage() {
  const [receipts, setReceipts] = useState([]);
  const [cameraMode, setCameraMode] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  // Start Camera
  const startCamera = async () => {
    try {
      setCameraMode(true);
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;
      videoRef.current.play();
    } catch {
      alert("❌ Could not access camera. Check permissions.");
    }
  };

  const stopCamera = () => {
    setCameraMode(false);
    const stream = videoRef.current?.srcObject;
    stream?.getTracks().forEach((t) => t.stop());
  };

  // Capture Photo
  const capturePhoto = async () => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    const ctx = canvas.getContext("2d");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      const file = new File([blob], `photo_${Date.now()}.jpg`, {
        type: "image/jpeg",
      });
      processReceipt(file);
      stopCamera();
    });
  };

  // Upload or Camera Capture → AI Extraction
  const processReceipt = async (file) => {
    setUploading(true);
    setMessage("⏳ Processing with AI...");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      if (data.success && data.receipt) {
        const r = data.receipt;
        const synced =
          data.quickbooks && data.quickbooks.success ? true : false;

        setReceipts((prev) => [
          ...prev,
          {
            id: Date.now(),
            name: file.name,
            url: URL.createObjectURL(file),
            vendor: r.Vendor,
            date: r.Date,
            amount: r.Amount ? `$${r.Amount}` : r.Total,
            category: r.Category,
            synced: synced,
          },
        ]);
        setMessage("✅ Receipt processed successfully!");
      } else {
        setMessage("⚠️ Could not extract data from receipt.");
      }
    } catch (err) {
      console.error(err);
      setMessage("❌ Upload failed. Please check your backend connection.");
    } finally {
      setUploading(false);
      setTimeout(() => setMessage(""), 3000);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-8">
      <div className="text-center mb-8">
        <h2 className="text-4xl font-extrabold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          Manage Your Receipts
        </h2>
        <p className="text-gray-600">
          Upload or capture receipts — AI will extract key info automatically.
        </p>
      </div>

      <div className="flex flex-col items-center gap-4 mb-10">
        <label
          htmlFor="file-upload"
          className="cursor-pointer w-full max-w-2xl border-2 border-dashed border-purple-300 bg-white rounded-2xl p-10 flex flex-col items-center justify-center text-center shadow hover:shadow-lg transition"
        >
          <CloudArrowUpIcon className="h-12 w-12 text-purple-500 mb-4" />
          <p className="text-gray-600 font-medium">
            Drag & drop your receipts or{" "}
            <span className="text-purple-600">browse</span>
          </p>
          <input
            id="file-upload"
            type="file"
            multiple
            className="hidden"
            ref={fileInputRef}
            onChange={(e) =>
              Array.from(e.target.files).forEach(processReceipt)
            }
          />
        </label>

        {!cameraMode && (
          <button
            onClick={startCamera}
            className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white px-5 py-2 rounded-xl shadow hover:scale-105 transition"
          >
            <CameraIcon className="h-5 w-5" />
            {uploading ? "Uploading..." : "Take Photo"}
          </button>
        )}
        {message && (
          <div className="text-sm text-center mt-3 font-medium text-purple-700">
            {message}
          </div>
        )}
      </div>

      {cameraMode && (
        <div className="flex flex-col items-center bg-gray-100 p-6 rounded-xl shadow-md">
          <video ref={videoRef} className="w-full max-w-md rounded-lg border" />
          <canvas ref={canvasRef} className="hidden" />
          <div className="flex gap-4 mt-4">
            <button
              onClick={capturePhoto}
              className="bg-green-600 text-white px-6 py-2 rounded-xl shadow hover:bg-green-700"
            >
              📸 Capture
            </button>
            <button
              onClick={stopCamera}
              className="bg-red-500 text-white px-6 py-2 rounded-xl shadow hover:bg-red-600"
            >
              ✕ Close
            </button>
          </div>
        </div>
      )}

      {/* Receipt Cards */}
      <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-6">
        {receipts.map((r) => (
          <div
            key={r.id}
            className="bg-white p-4 rounded-2xl shadow-md border hover:shadow-xl transition relative"
          >
            {/* ✅ QuickBooks Synced Badge */}
            {r.synced && (
              <div className="absolute top-3 right-3 bg-green-100 text-green-700 text-xs font-semibold px-3 py-1 rounded-full shadow-sm border border-green-300 animate-pulse">
                ✅ QuickBooks Synced
              </div>
            )}

            <img
              src={r.url}
              alt={r.name}
              className="rounded-xl h-40 w-full object-cover mb-3"
            />
            <h3 className="font-semibold text-lg text-gray-800">{r.vendor}</h3>
            <p className="text-sm text-gray-500">{r.date}</p>
            <div className="mt-2 flex justify-between text-sm text-gray-700">
              <span>{r.category}</span>
              <span className="font-bold text-green-600">{r.amount}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
