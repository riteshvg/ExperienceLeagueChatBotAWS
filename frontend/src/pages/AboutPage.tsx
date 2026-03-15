import { useEffect, useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Divider,
  Chip,
  Grid,
  Card,
  CardContent,
  Alert,
} from '@mui/material'
import CodeIcon from '@mui/icons-material/Code'
import CloudIcon from '@mui/icons-material/Cloud'
import StorageIcon from '@mui/icons-material/Storage'
import UpdateIcon from '@mui/icons-material/Update'
import axios from 'axios'

export default function AboutPage() {
  const [kbUpdateDate, setKbUpdateDate] = useState<string | null>(null)
  const [kbUpdateError, setKbUpdateError] = useState<string | null>(null)

  useEffect(() => {
    const fetchKbUpdateDate = async () => {
      try {
        const getApiBaseUrl = (): string => {
          const envUrl = (import.meta as any).env?.VITE_API_URL
          if (envUrl) {
            return envUrl
          }
          if (import.meta.env.PROD) {
            return ''
          }
          return 'http://localhost:8000'
        }
        const API_BASE_URL = getApiBaseUrl()
        const response = await axios.get(`${API_BASE_URL}/api/v1/kb/update-date`)
        
        if (response.data.success && response.data.last_updated) {
          const date = new Date(response.data.last_updated)
          const formatted = date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })
          setKbUpdateDate(formatted)
        } else {
          setKbUpdateError('Knowledge Base update date not available')
        }
      } catch (error) {
        console.error('Failed to fetch KB update date:', error)
        setKbUpdateError('Unable to fetch Knowledge Base update date')
      }
    }

    fetchKbUpdateDate()
  }, [])

  return (
    <Box>
      <Paper sx={{ p: 4, mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          About This Chatbot
        </Typography>
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body1" fontWeight="bold">
            ⚠️ Unofficial Application
          </Typography>
          <Typography variant="body2">
            This is an <strong>unofficial</strong> chatbot application. It is not affiliated with, 
            endorsed by, or connected to Adobe Inc. or Experience League. This tool is provided 
            as-is for educational and informational purposes only.
          </Typography>
        </Alert>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          Knowledge Base Information
        </Typography>
        <Box sx={{ my: 2 }}>
          {kbUpdateDate ? (
            <Chip
              icon={<UpdateIcon />}
              label={`Last Article Update: ${kbUpdateDate}`}
              color="primary"
              sx={{ fontSize: '1rem', py: 2, px: 1 }}
            />
          ) : kbUpdateError ? (
            <Typography variant="body2" color="error">
              {kbUpdateError}
            </Typography>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Loading update date...
            </Typography>
          )}
        </Box>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          Technology Stack
        </Typography>
        <Grid container spacing={3} sx={{ mt: 2 }}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <CodeIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6">Frontend</Typography>
                </Box>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  <Chip label="React" size="small" />
                  <Chip label="TypeScript" size="small" />
                  <Chip label="Material-UI" size="small" />
                  <Chip label="Vite" size="small" />
                  <Chip label="React Router" size="small" />
                  <Chip label="Zustand" size="small" />
                  <Chip label="Axios" size="small" />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <CloudIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6">Backend</Typography>
                </Box>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  <Chip label="FastAPI" size="small" />
                  <Chip label="Python 3.11" size="small" />
                  <Chip label="Uvicorn" size="small" />
                  <Chip label="WebSockets" size="small" />
                  <Chip label="Pydantic" size="small" />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <CloudIcon sx={{ mr: 1, color: 'secondary.main' }} />
                  <Typography variant="h6">AWS Services</Typography>
                </Box>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  <Chip label="AWS Bedrock" size="small" color="secondary" />
                  <Chip label="Claude 3 Haiku" size="small" color="secondary" />
                  <Chip label="Claude 3 Sonnet" size="small" color="secondary" />
                  <Chip label="Claude 3 Opus" size="small" color="secondary" />
                  <Chip label="Bedrock Knowledge Base" size="small" color="secondary" />
                  <Chip label="Amazon S3" size="small" color="secondary" />
                  <Chip label="Titan Embeddings" size="small" color="secondary" />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <StorageIcon sx={{ mr: 1, color: 'success.main' }} />
                  <Typography variant="h6">Infrastructure</Typography>
                </Box>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  <Chip label="Railway" size="small" color="success" />
                  <Chip label="Nixpacks" size="small" color="success" />
                  <Chip label="Docker" size="small" color="success" />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Divider sx={{ my: 4 }} />

        <Typography variant="h5" gutterBottom>
          Features
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li" variant="body1" sx={{ mb: 1 }}>
            <strong>Smart AI Routing:</strong> Automatically selects optimal AWS Bedrock models 
            (Claude 3 Haiku, Sonnet, Opus) based on query complexity
          </Typography>
          <Typography component="li" variant="body1" sx={{ mb: 1 }}>
            <strong>Knowledge Base Integration:</strong> Retrieves relevant documentation from 
            AWS Bedrock Knowledge Base
          </Typography>
          <Typography component="li" variant="body1" sx={{ mb: 1 }}>
            <strong>Real-time Streaming:</strong> WebSocket-based streaming responses for 
            immediate feedback
          </Typography>
          <Typography component="li" variant="body1" sx={{ mb: 1 }}>
            <strong>Caching & Session Management:</strong> LRU cache and session persistence 
            for improved performance
          </Typography>
          <Typography component="li" variant="body1" sx={{ mb: 1 }}>
            <strong>Source Links:</strong> Provides links to original Experience League articles
          </Typography>
          <Typography component="li" variant="body1" sx={{ mb: 1 }}>
            <strong>Video Links:</strong> Extracts and displays video links from documentation
          </Typography>
        </Box>

        <Divider sx={{ my: 4 }} />

        <Typography variant="h5" gutterBottom>
          Disclaimer
        </Typography>
        <Alert severity="warning" sx={{ mt: 2 }}>
          <Typography variant="body2">
            This application is provided for informational purposes only. While we strive to 
            provide accurate information, we make no warranties about the completeness, reliability, 
            or accuracy of the responses. Always refer to the official Adobe Experience League 
            documentation for authoritative information.
          </Typography>
        </Alert>
      </Paper>
    </Box>
  )
}
