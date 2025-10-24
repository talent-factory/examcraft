/**
 * RAG Exam Creator Component
 * Creates exams using RAG (Retrieval-Augmented Generation)
 *
 * This component dynamically loads the Premium implementation if available,
 * otherwise shows an upgrade prompt.
 */

import React, { lazy, Suspense, useState, useEffect } from 'react';
import { Box, Typography, Alert, Button, CircularProgress } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { InfoOutlined } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

interface RAGExamCreatorProps {
  selectedDocuments?: number[];
  onExamGenerated?: (exam: any) => void;
  onBack?: () => void;
}

// Try to lazy load Premium component
let PremiumRAGExamCreator: React.ComponentType<RAGExamCreatorProps> | null = null;

try {
  // Attempt to load Premium component from mounted volume
  PremiumRAGExamCreator = lazy(() =>
    import('/app/premium/src/components/RAGExamCreator.tsx')
      .catch(() => {
        console.log('Premium RAGExamCreator not available - using Core placeholder');
        return { default: () => null };
      })
  );
} catch (error) {
  console.log('Premium package not mounted');
}

const RAGExamCreator: React.FC<RAGExamCreatorProps> = (props) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [hasPremiumAccess, setHasPremiumAccess] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkPremiumAccess();
  }, [user]);

  const checkPremiumAccess = async () => {
    try {
      // Check if user has Premium/Professional/Enterprise tier
      if (!user?.institution_id) {
        setHasPremiumAccess(false);
        setLoading(false);
        return;
      }

      // Fetch user's tier from backend
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
        // Allow access for starter, professional, and enterprise tiers
        const premiumTiers = ['starter', 'professional', 'enterprise'];
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
  if (hasPremiumAccess && PremiumRAGExamCreator) {
    return (
      <Suspense fallback={
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
          <CircularProgress />
        </Box>
      }>
        <PremiumRAGExamCreator {...props} />
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
          RAG Exam Creator - Premium Feature
        </Typography>
        <Typography variant="body2" sx={{ mb: 2 }}>
          The RAG Exam Creator feature is available in the Premium package.
          This feature allows you to automatically generate exam questions from your documents using AI-powered RAG (Retrieval-Augmented Generation).
        </Typography>
        <Typography variant="body2" color="textSecondary">
          To access this feature, please upgrade to the Premium plan.
        </Typography>
      </Alert>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={() => props.onBack ? props.onBack() : navigate('/exams')}
        >
          Back
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

export default RAGExamCreator;

