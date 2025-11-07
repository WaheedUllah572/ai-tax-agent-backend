import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";

import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import ChatbotPage from "./pages/ChatbotPage";
import JoinTaxMate from "./pages/JoinTaxMate";
import SubscriptionSuccess from "./pages/SubscriptionSuccess";
import SubscriptionCancel from "./pages/SubscriptionCancel";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import ReceiptsPage from "./pages/ReceiptsPage";
import MileagePage from "./pages/MileagePage";
import ReportsPage from "./pages/ReportsPage";
import QBCompanyInfo from "./pages/quickbooks/CompanyInfo";
import QBCustomers from "./pages/quickbooks/Customers";
import QBInvoices from "./pages/quickbooks/Invoices";
import QBAccounts from "./pages/quickbooks/Accounts";
import QBExpenses from "./pages/quickbooks/Expenses";

function ProtectedRoute({ children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/chatbot" element={<ChatbotPage />} />
        <Route path="/join" element={<JoinTaxMate />} />
        <Route path="/receipts" element={<ReceiptsPage />} />
        <Route path="/mileage" element={<MileagePage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/quickbooks/companyinfo" element={<QBCompanyInfo />} />
        <Route path="/quickbooks/customers" element={<QBCustomers />} />
        <Route path="/quickbooks/invoices" element={<QBInvoices />} />
        <Route path="/quickbooks/accounts" element={<QBAccounts />} />
        <Route path="/quickbooks/expenses" element={<QBExpenses />} />
      </Route>

      <Route path="/subscription-success" element={<SubscriptionSuccess />} />
      <Route path="/subscription-cancel" element={<SubscriptionCancel />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

export default App;
