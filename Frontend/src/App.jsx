import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import DashboardLayout from './components/DashboardLayout';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import VerifyEmail from './pages/VerifyEmail';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Dashboard from './pages/Dashboard';
import UploadCSV from './pages/UploadCSV';
import UserManagement from './pages/UserManagement';
import CompanyManagement from './pages/CompanyManagement';
import Profile from './pages/Profile';
import TimetableManagement from './pages/TimetableManagement';
import MarksManagement from './pages/MarksManagement';
import CertificateManagement from './pages/CertificateManagement';
import Leaderboard from './pages/Leaderboard';
import Skills from './pages/Skills';
import AIInterview from './pages/AIInterview';
import Jobs from './pages/Jobs';
import Interviews from './pages/Interviews';
import RecruiterClgs from './pages/RecruiterClgs';
import Messages from './pages/Messages';
import Applications from './pages/Applications';
import Notifications from './pages/Notifications';
import CareerGuidance from './pages/CareerGuidance';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />

          {/* Protected Dashboard Routes */}
          <Route path="/dashboard" element={<ProtectedRoute />}>
            <Route element={<DashboardLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="users" element={<UserManagement />} />
              <Route path="all-users" element={<UserManagement allUsers />} />
              <Route path="colleges" element={<UserManagement colleges />} />
              <Route path="companies" element={<CompanyManagement />} />
              <Route path="upload-csv" element={<UploadCSV />} />
              <Route path="analytics" element={<Dashboard analytics />} />
              <Route path="interviews" element={<Interviews />} />
              <Route path="profile" element={<Profile />} />
              <Route path="skills" element={<Skills />} />
              <Route path="interview" element={<AIInterview />} />
              <Route path="timetable" element={<TimetableManagement />} />
              <Route path="marks" element={<MarksManagement />} />
              <Route path="certificates" element={<CertificateManagement />} />
              <Route path="leaderboard" element={<Leaderboard />} />
              <Route path="jobs" element={<Jobs />} />
              <Route path="applications" element={<Applications />} />
              <Route path="clgs" element={<RecruiterClgs />} />
              <Route path="messages" element={<Messages />} />
              <Route path="notifications" element={<Notifications />} />
              <Route path="career-guidance" element={<CareerGuidance />} />
              <Route path="departments" element={<Dashboard departments />} />
            </Route>
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="colored"
      />
    </AuthProvider>
  );
}

export default App;
