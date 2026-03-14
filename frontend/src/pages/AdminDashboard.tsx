import { Box, Typography, Paper, Alert } from '@mui/material'

export default function AdminDashboard() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        🔧 Admin Dashboard
      </Typography>
      <Alert severity="info" sx={{ mt: 2 }}>
        Admin dashboard is being migrated. Full functionality coming soon.
      </Alert>
      <Paper sx={{ p: 3, mt: 2 }}>
        <Typography variant="body1">
          This section will include:
        </Typography>
        <ul>
          <li>System status monitoring</li>
          <li>AWS configuration</li>
          <li>Knowledge Base status</li>
          <li>Analytics dashboard</li>
          <li>Cost tracking</li>
        </ul>
      </Paper>
    </Box>
  )
}

