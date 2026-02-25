import {
    FiHome, FiUsers, FiUpload, FiCheckSquare, FiBarChart2,
    FiBookOpen, FiBriefcase, FiSettings
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
        { path: '/dashboard/upload-csv', label: 'Upload CSV', icon: FiUpload },
        { path: '/dashboard/all-users', label: 'All Users', icon: FiBookOpen },
    ],
    HOD: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/users', label: 'Manage Faculty', icon: FiUsers },
        { path: '/dashboard/upload-csv', label: 'Upload CSV', icon: FiUpload },
    ],
    FACULTY: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/users', label: 'Manage Students', icon: FiUsers },
        { path: '/dashboard/upload-csv', label: 'Upload CSV', icon: FiUpload },
    ],
    STUDENT: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/profile', label: 'My Profile', icon: FiSettings },
    ],
    COMPANY_ADMIN: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/users', label: 'Manage Recruiters', icon: FiUsers },
        { path: '/dashboard/upload-csv', label: 'Upload CSV', icon: FiUpload },
    ],
    RECRUITER: [
        { path: '/dashboard', label: 'Dashboard', icon: FiHome },
        { path: '/dashboard/interviews', label: 'Interviews', icon: FiBriefcase },
    ],
};
