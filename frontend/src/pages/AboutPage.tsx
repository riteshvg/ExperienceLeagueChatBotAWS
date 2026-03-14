import { Box, Typography, Paper, Grid } from '@mui/material'

export default function AboutPage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        ℹ️ About This Application
      </Typography>

      <Paper sx={{ p: 3, mt: 2 }}>
        <Typography variant="h6" gutterBottom>
          🎯 What is this application?
        </Typography>
        <Typography variant="body1" paragraph>
          This is an intelligent chatbot designed specifically to help you with Adobe Analytics
          and Customer Journey Analytics (CJA) questions. Think of it as your personal Adobe
          expert that's available 24/7!
        </Typography>
      </Paper>

      <Grid container spacing={2} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              🤖 Smart AI Assistant
            </Typography>
            <Typography variant="body2" paragraph>
              - Powered by advanced AI technology
            </Typography>
            <Typography variant="body2" paragraph>
              - Understands Adobe-specific terminology
            </Typography>
            <Typography variant="body2">
              - Provides accurate, helpful answers
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              📚 Knowledge Base
            </Typography>
            <Typography variant="body2" paragraph>
              - Access to comprehensive Adobe documentation
            </Typography>
            <Typography variant="body2" paragraph>
              - Up-to-date information and best practices
            </Typography>
            <Typography variant="body2">
              - Real-world examples and use cases
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

