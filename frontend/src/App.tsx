import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Meters from "./pages/Meters";

export default function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <strong>SUNRISE HES</strong>
          <span>نظام رأس الخط للمقاييس الذكية</span>
        </div>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            لوحة التحكم
          </NavLink>
          <NavLink to="/meters" className={({ isActive }) => (isActive ? "active" : "")}>
            المقاييس
          </NavLink>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/meters" element={<Meters />} />
      </Routes>
    </div>
  );
}
