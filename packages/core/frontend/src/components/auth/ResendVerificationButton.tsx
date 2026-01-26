import React, { useState } from 'react';
import { Button, Alert, CircularProgress, Box } from '@mui/material';
import EmailIcon from '@mui/icons-material/Email';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface ResendVerificationButtonProps {
  email: string;
  variant?: 'text' | 'outlined' | 'contained';
  fullWidth?: boolean;
}

const ResendVerificationButton: React.FC<ResendVerificationButtonProps> = ({
  email,
  variant = 'text',
  fullWidth = false,
}) => {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleResend = async () => {
    setLoading(true);
    setSuccess(false);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/resend-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to resend verification email');
      }

      setSuccess(true);

      // Reset success message after 5 seconds
      setTimeout(() => {
        setSuccess(false);
      }, 5000);
    } catch (err: any) {
      setError(err.message || 'Failed to resend verification email');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Button
        variant={variant}
        onClick={handleResend}
        disabled={loading || success}
        startIcon={loading ? <CircularProgress size={20} /> : <EmailIcon />}
        fullWidth={fullWidth}
        sx={{
          textTransform: 'none',
          ...(variant === 'contained' && {
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            '&:hover': {
              background: 'linear-gradient(135deg, #5568d3 0%, #63408a 100%)',
            },
          }),
        }}
      >
        {loading ? 'Sending...' : success ? 'Email Sent!' : 'Resend Verification Email'}
      </Button>

      {success && (
        <Alert severity="success" sx={{ mt: 2 }}>
          Verification email sent! Please check your inbox.
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Box>
  );
};

export default ResendVerificationButton;
