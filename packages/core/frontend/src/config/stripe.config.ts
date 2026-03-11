/**
 * Stripe Configuration
 *
 * Update these Price IDs after creating products in Stripe Dashboard
 * Dashboard: https://dashboard.stripe.com/test/products
 */

export interface StripePriceConfig {
  starter: string;
  professional: string;
}

/**
 * Stripe Price IDs
 *
 * IMPORTANT: Replace these placeholder values with actual Stripe Price IDs
 * after creating products in your Stripe Dashboard.
 *
 * Format: price_xxxxxxxxxxxxxxxxxxxxx
 *
 * To update:
 * 1. Create products in Stripe Dashboard
 * 2. Copy the Price ID from each product
 * 3. Update the values below
 */
export const STRIPE_PRICES: StripePriceConfig = {
  // Starter Plan - CHF 19/month
  starter: process.env.REACT_APP_STRIPE_PRICE_STARTER || 'price_placeholder_starter',

  // Professional Plan - CHF 149/month
  professional: process.env.REACT_APP_STRIPE_PRICE_PROFESSIONAL || 'price_placeholder_professional',
};

/**
 * Check if Stripe is properly configured
 */
export const isStripeConfigured = (): boolean => {
  return !STRIPE_PRICES.starter.includes('placeholder') &&
         !STRIPE_PRICES.professional.includes('placeholder');
};

/**
 * Stripe Configuration Status
 */
export const getStripeConfigStatus = (): {
  configured: boolean;
  message: string;
} => {
  if (isStripeConfigured()) {
    return {
      configured: true,
      message: 'Stripe is configured and ready to use'
    };
  }

  return {
    configured: false,
    message: 'Stripe Price IDs need to be configured. Please update stripe.config.ts with actual Price IDs from your Stripe Dashboard.'
  };
};
