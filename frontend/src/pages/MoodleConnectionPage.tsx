/**
 * /admin/integrations/moodle (TF-336 Subarea C).
 *
 * Wrapper-Page um den ``MoodleConnectionForm``. Eigene Page (statt Tab
 * im Admin) entspricht dem `/admin/integrations/<system>`-Schema, das
 * weitere Integrationen (ILIAS, Generic-CSV, …) später aufnehmen kann.
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
