/**
 * /admin/integrations/moodle (TF-336 Subarea C).
 *
 * Wrapper page around ``MoodleConnectionForm``. A dedicated page (instead
 * of a tab in Admin) matches the `/admin/integrations/<system>` scheme,
 * which can later accommodate further integrations (ILIAS, generic CSV, …).
 */

import React from 'react';
import { Box } from '@mui/material';

import MoodleConnectionForm from '../components/admin/MoodleConnectionForm';

const MoodleConnectionPage: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <MoodleConnectionForm />
    </Box>
  );
};

export default MoodleConnectionPage;
