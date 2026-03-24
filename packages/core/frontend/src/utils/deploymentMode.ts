/**
 * Deployment Mode Detection Utility
 *
 * Detects whether the application is running in Core or Full deployment mode.
 * Used for runtime loading of Premium/Enterprise features.
 */

export type DeploymentMode = 'core' | 'full';

/**
 * Get the current deployment mode from environment variables
 */
export const getDeploymentMode = (): DeploymentMode => {
  const mode = process.env.REACT_APP_DEPLOYMENT_MODE?.toLowerCase();
  return mode === 'full' ? 'full' : 'core';
};

/**
 * Check if running in Full deployment (Premium + Enterprise)
 */
export const isFullDeployment = (): boolean => {
  return getDeploymentMode() === 'full';
};

/**
 * Check if running in Core deployment (OpenSource)
 */
export const isCoreDeployment = (): boolean => {
  return getDeploymentMode() === 'core';
};

/**
 * Check if a Premium/Enterprise package is available
 * @param packageName - Name of the package (e.g., 'premium', 'enterprise')
 */
export const isPackageAvailable = async (packageName: 'premium' | 'enterprise'): Promise<boolean> => {
  if (!isFullDeployment()) {
    return false;
  }

  try {
    // Try to import a marker file from the package
    await import(`../${packageName}/package.json`);
    return true;
  } catch {
    return false;
  }
};

/**
 * Log deployment mode information (for debugging)
 */
export const logDeploymentInfo = (): void => {
  const mode = getDeploymentMode();
  console.log(`🚀 ExamCraft AI - Running in ${mode.toUpperCase()} mode`);

  if (mode === 'full') {
    console.log('✅ Premium/Enterprise features available (controlled by RBAC)');
  } else {
    console.log('ℹ️  Core deployment - Premium/Enterprise features disabled');
  }
};
