import axios from "axios";

// ✅ Stable backend base URL
const API_BASE_URL =
  import.meta?.env?.VITE_API_BASE_URL?.trim() ||
  process.env.REACT_APP_API_BASE_URL?.trim() ||
  "https://ai-tax-agent-backend-klwl.onrender.com";

// ✅ Axios instance
const API = axios.create({
  baseURL: `${API_BASE_URL}/quickbooks`,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

// ✅ QuickBooks Endpoints
export const getCompanyInfo = () => API.get("/status");
export const getCustomers = () => API.get("/customers");
export const getInvoices = () => API.get("/invoices");
export const getAccounts = () => API.get("/accounts");
export const addExpense = (data) => API.post("/expenses", data);

export default API;
