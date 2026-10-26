import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";

import Home from "./pages/Home";
import Roster from "./pages/Roster";
import Vzp from "./pages/Vzp";
import Online from "./pages/Online";
import Gatherings from "./pages/Gatherings";
import StaffLogin from "./pages/staff/Login";
import StaffDashboard from "./pages/staff/Dashboard";
import StaffApplications from "./pages/staff/Applications";
import StaffTicket from "./pages/staff/Ticket";
import StaffGatherings from "./pages/staff/Gatherings";

export default function App() {
  return (
    <>
      <header className="nav">
        <Link className="brand" to="/">
          ★ Akiyama Family
        </Link>
        <nav>
          <NavLink to="/">Главная</NavLink>
          <NavLink to="/roster">Состав</NavLink>
          <NavLink to="/vzp">VZP</NavLink>
          <NavLink to="/online">Онлайн</NavLink>
          <NavLink to="/gatherings">Сборы</NavLink>
          <NavLink to="/staff">Панель</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/roster" element={<Roster />} />
          <Route path="/vzp" element={<Vzp />} />
          <Route path="/online" element={<Online />} />
          <Route path="/gatherings" element={<Gatherings />} />
          <Route path="/staff" element={<StaffDashboard />} />
          <Route path="/staff/login" element={<StaffLogin />} />
          <Route path="/staff/applications" element={<StaffApplications />} />
          <Route path="/staff/applications/:ticketId" element={<StaffTicket />} />
          <Route path="/staff/gatherings" element={<StaffGatherings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="footer">Akiyama Family · GTA5RP</footer>
    </>
  );
}
