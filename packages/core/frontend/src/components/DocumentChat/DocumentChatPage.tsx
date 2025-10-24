/**
 * Document Chat Page Component
 * Allows users to chat with documents using RAG
 *
 * This component dynamically loads the Premium implementation if available,
 * otherwise shows an upgrade prompt.
 */

import React, { lazy, Suspense, useState, useEffect } from 'react';
import { Box, Typography, Alert, Button, CircularProgress } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { InfoOutlined } from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';

// Try to lazy load Premium component
let PremiumDocumentChatPage: React.ComponentType | null = null;

try {
  PremiumDocumentChatPage = lazy(() =>
    import('/app/premium/src/components/DocumentChat/DocumentChatPage.tsx')
      .catch(() => {
        console.log('Premium DocumentChatPage not available - using Core placeholder');
        return { default: () => null };
      })
  );
} catch (error) {
  console.log('Premium package not mounted');
}

export const DocumentChatPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [hasPremiumAccess, setHasPremiumAccess] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkPremiumAccess();
  }, [user]);

  const checkPremiumAccess = async () => {
    try {
      if (!user?.institution_id) {
        setHasPremiumAccess(false);
        setLoading(false);
        return;
      }

      const token = localStorage.getItem('examcraft_access_token');
      if (!token) {
        setHasPremiumAccess(false);
        setLoading(false);
        return;
      }

      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/v1/rbac/tiers/my`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        // Document Chat requires Professional or Enterprise tier
        const premiumTiers = ['professional', 'enterprise'];
        setHasPremiumAccess(premiumTiers.includes(data.tier?.toLowerCase()));
      } else {
        setHasPremiumAccess(false);
      }
    } catch (error) {
      console.error('Error checking premium access:', error);
      setHasPremiumAccess(false);
    } finally {
      setLoading(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  // If user has premium access and Premium component is available, use it
  if (hasPremiumAccess && PremiumDocumentChatPage) {
    return (
      <Suspense fallback={
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
          <CircularProgress />
        </Box>
      }>
        <PremiumDocumentChatPage />
      </Suspense>
    );
  }

  // Otherwise show upgrade prompt
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        gap: 3,
        p: 2,
      }}
    >
      <Alert
        severity="info"
        icon={<InfoOutlined />}
        sx={{ maxWidth: 600 }}
      >
        <Typography variant="h6" sx={{ mb: 1 }}>
          Document Chat - Premium Feature
        </Typography>
        <Typography variant="body2" sx={{ mb: 2 }}>
          The Document Chat feature is available in the Premium package.
          This feature allows you to have interactive conversations with your documents using AI-powered RAG (Retrieval-Augmented Generation).
        </Typography>
        <Typography variant="body2" color="textSecondary">
          To access this feature, please upgrade to the Professional or Enterprise plan.
        </Typography>
      </Alert>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={() => navigate('/documents')}
        >
          Back to Documents
        </Button>
        <Button
          variant="outlined"
          color="primary"
          href="https://examcraft.ai/pricing"
          target="_blank"
        >
          View Premium Plans
        </Button>
      </Box>
    </Box>
  );
};

