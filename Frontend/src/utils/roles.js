import {
    FiHome, FiUsers, FiUpload, FiCheckSquare, FiBarChart2,
    FiBookOpen, FiBriefcase, FiSettings, FiCalendar, FiFileText, FiAward, FiLayers, FiTrendingUp
} from 'react-icons/fi';

// Role constants
export const ROLES = {
    CUDAS_ADMIN: 'CUDAS_ADMIN',
    COLLEGE_PRINCIPAL: 'COLLEGE_PRINCIPAL',
    HOD: 'HOD',
    FACULTY: 'FACULTY',
    STUDENT: 'STUDENT',
    COMPANY_ADMIN: 'COMPANY_ADMIN',
    RECRUITER: 'RECRUITER',
};

// Display labels
export const ROLE_LABELS = {
    CUDAS_ADMIN: 'CUDAS Admin',
    COLLEGE_PRINCIPAL: 'College Principal',
    HOD: 'Head of Department',
    FACULTY: 'Faculty',
    STUDENT: 'Student',
    COMPANY_ADMIN: 'Company Admin',
    RECRUITER: 'Recruiter',
};

// Which child role each parent can create
export const CHILD_ROLE_MAP = {
    COLLEGE_PRINCIPAL: 'HOD',
    HOD: 'FACULTY',
    FACULTY: 'STUDENT',
    COMPANY_ADMIN: 'RECRUITER',
};

// Sidebar routes per role
export const SIDEBAR_ROUTES = {
    CUDAS_ADMIN: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/colleges', label: 'Manage Colleges', icon: FiCheckSquare },
        { path: '/dashboard/companies', label: 'Manage Companies', icon: FiBriefcase },
        { path: '/dashboard/analytics', label: 'Analytics', icon: FiBarChart2 },
    ],
    COLLEGE_PRINCIPAL: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/users', label: 'Manage HODs', icon: FiUsers },
        { path: '/dashboard/departments', label: 'Department Summary', icon: FiLayers },
        { path: '/dashboard/upload-csv', label: 'Upload CSV', icon: FiUpload },
        { path: '/dashboard/all-users', label: 'All Users', icon: FiBookOpen },
        { path: '/dashboard/leaderboard', label: 'Leaderboard', icon: FiTrendingUp },
        { path: '/dashboard/profile', label: 'My Profile', icon: FiSettings },
    ],
    HOD: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/users', label: 'Manage Faculty', icon: FiUsers },
        { path: '/dashboard/timetable', label: 'Exam Timetable', icon: FiCalendar },
        { path: '/dashboard/marks', label: 'Marks Monitoring', icon: FiFileText },
        { path: '/dashboard/upload-csv', label: 'Upload CSV', icon: FiUpload },
        { path: '/dashboard/leaderboard', label: 'Leaderboard', icon: FiTrendingUp },
        { path: '/dashboard/profile', label: 'My Profile', icon: FiSettings },
    ],
    FACULTY: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/users', label: 'Manage Students', icon: FiUsers },
        { path: '/dashboard/marks', label: 'Add Marks', icon: FiFileText },
        { path: '/dashboard/upload-csv', label: 'Upload CSV', icon: FiUpload },
        { path: '/dashboard/leaderboard', label: 'Leaderboard', icon: FiTrendingUp },
        { path: '/dashboard/profile', label: 'My Profile', icon: FiSettings },
    ],
    STUDENT: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/timetable', label: 'Exam Timetable', icon: FiCalendar },
        { path: '/dashboard/certificates', label: 'Certificates', icon: FiAward },
        { path: '/dashboard/skills', label: 'Skills', icon: FiFileText },
        { path: '/dashboard/interview', label: 'AI Interview', icon: FiBriefcase },
        { path: '/dashboard/leaderboard', label: 'Leaderboard', icon: FiTrendingUp },
        { path: '/dashboard/profile', label: 'My Profile', icon: FiSettings },
    ],
    COMPANY_ADMIN: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/users', label: 'Manage Recruiters', icon: FiUsers },
        { path: '/dashboard/upload-csv', label: 'Upload CSV', icon: FiUpload },
        { path: '/dashboard/profile', label: 'My Profile', icon: FiSettings },
    ],
    RECRUITER: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/interviews', label: 'Interviews', icon: FiBriefcase },
    ],
};
