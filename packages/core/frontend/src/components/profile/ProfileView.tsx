/**
 * Profile View Component
 * Display user profile information
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getDateLocale } from '../../utils/dateLocale';
import { useAuth } from '../../contexts/AuthContext';

interface ProfileViewProps {
  onEdit?: () => void;
}

export const ProfileView: React.FC<ProfileViewProps> = ({ onEdit }) => {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [avatarError, setAvatarError] = useState(false);

  if (!user) {
    return (
      <div className="text-center py-8 text-gray-500">
        {t('profile.profileView.noUserData')}
      </div>
    );
  }

  // Get proxied avatar URL to avoid Google rate limiting (429 errors)
  const getAvatarUrl = (userId: number): string => {
    const API_BASE_URL = process.env.REACT_APP_API_URL;

    if (!API_BASE_URL) {
      console.error('REACT_APP_API_URL is not configured. Avatar proxy will not work.');
      return ''; // Return empty string to trigger onError fallback
    }

    return `${API_BASE_URL}/api/auth/avatar/${userId}`;
  };

  return (
    <div className="bg-white shadow rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h2 className="text-xl font-semibold text-gray-800">{t('profile.profileView.sectionHeader')}</h2>
        {onEdit && (
          <button
            type="button"
            onClick={onEdit}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {t('profile.profileView.editButton')}
          </button>
        )}
      </div>

      {/* Profile Content */}
      <div className="px-6 py-6 space-y-6">
        {/* Avatar Section */}
        <div className="flex items-center space-x-4">
          {/* Avatar with fallback to initials */}
          {user.id && !avatarError ? (
            <img
              src={getAvatarUrl(user.id)}
              alt={`${user.first_name} ${user.last_name}`}
              className="w-20 h-20 rounded-full object-cover border-2 border-gray-200"
              onError={() => setAvatarError(true)}
            />
          ) : (
            <div className="w-20 h-20 bg-blue-600 rounded-full flex items-center justify-center text-white text-3xl font-bold border-2 border-gray-200">
              {user.first_name?.[0] || user.email?.[0]?.toUpperCase() || '?'}{user.last_name?.[0] || ''}
            </div>
          )}
          <div>
            <h3 className="text-2xl font-bold text-gray-900">
              {user.first_name && user.last_name
                ? `${user.first_name} ${user.last_name}`
                : user.email || t('profile.profileView.unnamedUser')}
            </h3>
            <p className="text-gray-600">{user.email}</p>
            {user.oauth_provider && (
              <p className="text-sm text-gray-500 mt-1">
                🔗 {t('profile.profileView.connectedVia')} {user.oauth_provider.charAt(0).toUpperCase() + user.oauth_provider.slice(1)}
              </p>
            )}
          </div>
        </div>

        {/* Information Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.profileView.emailAddress')}
            </label>
            <p className="text-gray-900">{user.email}</p>
          </div>

          {/* First Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.profileView.firstName')}
            </label>
            <p className="text-gray-900">{user.first_name}</p>
          </div>

          {/* Last Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.profileView.lastName')}
            </label>
            <p className="text-gray-900">{user.last_name}</p>
          </div>

          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.profileView.accountStatus')}
            </label>
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              user.status === 'active'
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}>
              {user.status}
            </span>
          </div>

          {/* Institution */}
          {user.institution && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('profile.profileView.institution')}
              </label>
              <p className="text-gray-900">{user.institution.name}</p>
              <p className="text-sm text-gray-500">
                {user.institution.subscription_tier} tier
              </p>
            </div>
          )}

          {/* Roles */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.profileView.roles')}
            </label>
            <div className="flex flex-wrap gap-2">
              {user.roles.map((role) => (
                <span
                  key={role.id}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
                >
                  {role.display_name}
                </span>
              ))}
              {user.is_superuser && (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                  {t('profile.profileView.superuser')}
                </span>
              )}
            </div>
          </div>

          {/* Last Login */}
          {user.last_login && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('profile.profileView.lastLogin')}
              </label>
              <p className="text-gray-900">
                {new Date(user.last_login).toLocaleString(getDateLocale(i18n.language))}
              </p>
            </div>
          )}

          {/* Account Created */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.profileView.memberSince')}
            </label>
            <p className="text-gray-900">
              {new Date(user.created_at).toLocaleDateString(getDateLocale(i18n.language))}
            </p>
          </div>
        </div>

        {/* Permissions Section */}
        {user.roles.length > 0 && (
          <div className="pt-6 border-t border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              {t('profile.profileView.permissions')}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {Array.from(new Set(user.roles.flatMap(role => role.permissions))).map((permission) => (
                <div
                  key={permission}
                  className="flex items-center space-x-2 text-sm text-gray-700"
                >
                  <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span>{permission}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
