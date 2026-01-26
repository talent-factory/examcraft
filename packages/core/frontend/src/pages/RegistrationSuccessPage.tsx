import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Box, Container, Paper, Typography, Button, Alert } from '@mui/material';
import MarkEmailReadIcon from '@mui/icons-material/MarkEmailRead';
import ResendVerificationButton from '../components/auth/ResendVerificationButton';

const RegistrationSuccessPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const email = (location.state as any)?.email || '';

  const handleGoToDashboard = () => {
    navigate('/dashboard');
  };

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            width: '100%',
            textAlign: 'center',
          }}
        >
          <MarkEmailReadIcon
            sx={{ fontSize: 80, color: 'primary.main', mb: 2 }}
          />
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
            Registration Successful! 🎉
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Welcome to ExamCraft AI! We've sent a verification email to:
          </Typography>
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
              {email}
            </Typography>
          </Alert>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Please check your inbox and click the verification link to activate your account.
            The link will expire in 24 hours.
          </Typography>

          <Box sx={{ mb: 3 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Didn't receive the email?
            </Typography>
            {email && <ResendVerificationButton email={email} variant="outlined" fullWidth />}
          </Box>

          <Button
            variant="contained"
            size="large"
            onClick={handleGoToDashboard}
            fullWidth
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #5568d3 0%, #63408a 100%)',
              },
            }}
          >
            Continue to Dashboard
          </Button>

          <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
            You can still access the dashboard, but some features may be limited until you verify
            your email.
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default RegistrationSuccessPage;
