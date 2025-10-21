/**
 * Stats Card Component
 * Card for displaying statistics and metrics
 */

import React from 'react';

interface StatsCardProps {
  icon: string;
  label: string;
  value: string | number;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error';
}

const colorClasses = {
  primary: 'bg-primary-50 border-primary-200',
  secondary: 'bg-secondary-50 border-secondary-200',
  success: 'bg-green-50 border-green-200',
  warning: 'bg-yellow-50 border-yellow-200',
  error: 'bg-red-50 border-red-200',
};

const iconColorClasses = {
  primary: 'text-primary-600',
  secondary: 'text-secondary-600',
  success: 'text-green-600',
  warning: 'text-yellow-600',
  error: 'text-red-600',
};

const trendColorClasses = {
  up: 'text-green-600',
  down: 'text-red-600',
};

export const StatsCard: React.FC<StatsCardProps> = ({
  icon,
  label,
  value,
  trend,
  color = 'primary',
}) => {
  return (
    <div className={`card p-6 ${colorClasses[color]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600 mb-1">
            {label}
          </p>
          <p className="text-3xl font-bold text-gray-900">
            {value}
          </p>
          {trend && (
            <p className={`text-sm mt-2 ${trendColorClasses[trend.direction]}`}>
              {trend.direction === 'up' ? '↑' : '↓'} {Math.abs(trend.value)}%
            </p>
          )}
        </div>
        <div className={`text-3xl ${iconColorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
};

