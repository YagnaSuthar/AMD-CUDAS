import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import DashboardLayout from './components/DashboardLayout';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import Landing from './pages/Landing';
<<<<<<< HEAD
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
import Round2Meeting from './pages/Round2Meeting';
=======
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import VerifyEmail from './pages/auth/VerifyEmail';
import ForgotPassword from './pages/auth/ForgotPassword';
import ResetPassword from './pages/auth/ResetPassword';
import Dashboard from './pages/dashboard/college/Dashboard';
import UploadCSV from './pages/dashboard/college/features/UploadCSV';
import UserManagement from './pages/dashboard/college/features/UserManagement';
import CompanyManagement from './pages/dashboard/college/features/CompanyManagement';
import Profile from './pages/dashboard/college/features/Profile';
import TimetableManagement from './pages/dashboard/college/features/TimetableManagement';
import MarksManagement from './pages/dashboard/college/features/MarksManagement';
import CertificateManagement from './pages/dashboard/college/features/CertificateManagement';
import Leaderboard from './pages/dashboard/college/features/Leaderboard';
import Skills from './pages/dashboard/college/features/Skills';
import AIInterview from './pages/dashboard/college/features/AIInterview';
import Jobs from './pages/dashboard/college/features/Jobs';
import Interviews from './pages/dashboard/college/features/Interviews';
import RecruiterClgs from './pages/dashboard/recruiter/RecruiterClgs';
import Messages from './pages/dashboard/recruiter/Messages';
import Applications from './pages/dashboard/recruiter/Applications';
import Notifications from './pages/dashboard/college/features/Notifications';
import CareerGuidance from './pages/dashboard/college/features/CareerGuidance';
import Round2Meeting from './pages/dashboard/college/features/Round2Meeting';
import InterviewLive from './pages/dashboard/college/features/InterviewLive';
import AssignSubjects from './pages/dashboard/college/features/AssignSubjects';
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a

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
<<<<<<< HEAD
            <Route element={<DashboardLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="users" element={<UserManagement />} />
=======
            {/* InterviewLive renders fullscreen — no sidebar/header */}
            <Route path="interview/live" element={<InterviewLive />} />

            <Route element={<DashboardLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="users" element={<UserManagement />} />
              <Route path="assign-subjects" element={<AssignSubjects />} />
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
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
              <Route path="round2/:pipelineId" element={<Round2Meeting />} />
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
