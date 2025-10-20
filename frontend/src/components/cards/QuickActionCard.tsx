/**
 * Quick Action Card Component
 * Card for dashboard quick actions
 */

import React from 'react';
import { Link } from 'react-router-dom';

interface QuickActionCardProps {
  icon: string;
  title: string;
  description: string;
  path: string;
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error';
}

const colorClasses = {
  primary: 'bg-primary-50 border-primary-200 hover:border-primary-300',
  secondary: 'bg-secondary-50 border-secondary-200 hover:border-secondary-300',
  success: 'bg-green-50 border-green-200 hover:border-green-300',
  warning: 'bg-yellow-50 border-yellow-200 hover:border-yellow-300',
  error: 'bg-red-50 border-red-200 hover:border-red-300',
};

const iconColorClasses = {
  primary: 'text-primary-600',
  secondary: 'text-secondary-600',
  success: 'text-green-600',
  warning: 'text-yellow-600',
  error: 'text-red-600',
};

export const QuickActionCard: React.FC<QuickActionCardProps> = ({
  icon,
  title,
  description,
  path,
  color = 'primary',
}) => {
  return (
    <Link to={path} className="block h-full">
      <div
        className={`card p-6 h-full flex flex-col ${colorClasses[color]} transition-all duration-250 hover:shadow-lg`}
      >
        <div className={`text-4xl mb-4 ${iconColorClasses[color]}`}>
          {icon}
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          {title}
        </h3>
        <p className="text-sm text-gray-600 flex-1">
          {description}
        </p>
        <div className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-700">
          Öffnen →
        </div>
      </div>
    </Link>
  );
};

