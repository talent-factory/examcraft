/**
 * Navigation Bar Component
 * Role-based navigation with user menu
 */

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { PackageTierBadge } from './PackageTierBadge';

export const NavigationBar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Get proxied avatar URL to avoid Google rate limiting (429 errors)
  const getAvatarUrl = (userId: number): string => {
    const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    return `${API_BASE_URL}/api/auth/avatar/${userId}`;
  };

  return (
    <nav className="bg-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex-shrink-0 flex items-center space-x-4">
            <Link to="/dashboard" className="text-2xl font-bold text-primary-600 hover:text-primary-700 transition-colors">
              ExamCraft AI
            </Link>
            {/* Package Tier Badge */}
            <PackageTierBadge />
          </div>

          {/* User Menu */}
          <div className="flex items-center">
            {/* User Dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center space-x-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-full p-1 hover:bg-gray-100 transition-colors"
                aria-label="User menu"
              >
                {/* Avatar Image or Initials */}
                {user?.id ? (
                  <img
                    src={getAvatarUrl(user.id)}
                    alt={`${user.first_name} ${user.last_name}`}
                    className="w-8 h-8 rounded-full object-cover"
                    onError={(e) => {
                      // Fallback to initials if image fails to load
                      e.currentTarget.style.display = 'none';
                      const fallback = e.currentTarget.nextElementSibling as HTMLElement;
                      if (fallback) fallback.style.display = 'flex';
                    }}
                  />
                ) : null}
                <div
                  className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center text-white font-medium"
                  style={{ display: user?.id ? 'none' : 'flex' }}
                >
                  {user?.first_name?.[0]}{user?.last_name?.[0]}
                </div>
                <span className="text-gray-700 font-medium">
                  {user?.first_name} {user?.last_name}
                </span>
                <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* Dropdown Menu */}
              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50">
                  <div className="py-1">
                    <div className="px-4 py-2 text-xs text-gray-500 border-b">
                      {user?.email}
                    </div>
                    <Link
                      to="/profile"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      onClick={() => setShowUserMenu(false)}
                    >
                      👤 Profile
                    </Link>
                    <Link
                      to="/settings"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      onClick={() => setShowUserMenu(false)}
                    >
                      ⚙️ Settings
                    </Link>
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100"
                    >
                      🚪 Logout
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

