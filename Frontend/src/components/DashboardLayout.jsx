import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

export default function DashboardLayout() {
    const [sidebarOpen, setSidebarOpen] = useState(false);

    const toggleSidebar = () => setSidebarOpen(!sidebarOpen);
    const closeSidebar = () => setSidebarOpen(false);

    return (
        <div className="dashboard-layout">
            <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />
            <Header onMenuClick={toggleSidebar} />

            <main className="main-content fade-in">
                <Outlet />
            </main>
        </div>
    );
}
