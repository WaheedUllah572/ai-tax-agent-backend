import React, { createContext, useContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (storedUser) setUser(JSON.parse(storedUser));
  }, []);

  const login = (email, password) => {
    const storedUsers = JSON.parse(localStorage.getItem("users") || "[]");
    const existingUser = storedUsers.find((u) => u.email === email && u.password === password);

    if (existingUser) {
      setUser(existingUser);
      localStorage.setItem("user", JSON.stringify(existingUser));
      navigate("/");
    } else {
      alert("Invalid email or password ❌");
    }
  };

  const register = (name, email, password) => {
    const storedUsers = JSON.parse(localStorage.getItem("users") || "[]");
    const exists = storedUsers.find((u) => u.email === email);

    if (exists) {
      alert("User already exists. Please login.");
      navigate("/login");
      return;
    }

    const newUser = { name, email, password };
    localStorage.setItem("users", JSON.stringify([...storedUsers, newUser]));
    alert("✅ Registration successful. Please login.");
    navigate("/login"); // after register → go to login
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("user");
    navigate("/login");
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
