import { ReactNode, useEffect, useState } from 'react'
import { Box, AppBar, Toolbar, Typography, Button, Container, Chip } from '@mui/material'
import { Link } from 'react-router-dom'
import ChatIcon from '@mui/icons-material/Chat'
import InfoIcon from '@mui/icons-material/Info'
import SettingsIcon from '@mui/icons-material/Settings'
import UpdateIcon from '@mui/icons-material/Update'
import axios from 'axios'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const [kbUpdateDate, setKbUpdateDate] = useState<string | null>(null)

  useEffect(() => {
    // Fetch Knowledge Base update date
    const fetchKbUpdateDate = async () => {
      try {
        // In production, use relative URLs (same origin)
        // In development, use localhost
        const getApiBaseUrl = (): string => {
          const envUrl = (import.meta as any).env?.VITE_API_URL
          if (envUrl) {
            return envUrl
          }
          if (import.meta.env.PROD) {
            return '' // Empty string = same origin (relative URLs)
          }
          return 'http://localhost:8000'
        }
        const API_BASE_URL = getApiBaseUrl()
        const response = await axios.get(`${API_BASE_URL}/api/v1/kb/update-date`)
        
        if (response.data.success && response.data.last_updated) {
          const date = new Date(response.data.last_updated)
          const formatted = date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
          })
          setKbUpdateDate(formatted)
        }
      } catch (error) {
        console.error('Failed to fetch KB update date:', error)
      }
    }

    fetchKbUpdateDate()
  }, [])

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            📊 Adobe Experience League Chatbot (Unofficial)
          </Typography>
          {kbUpdateDate && (
            <Chip
              icon={<UpdateIcon />}
              label={`KB Updated: ${kbUpdateDate}`}
              size="small"
              sx={{
                mr: 2,
                backgroundColor: 'rgba(255, 255, 255, 0.2)',
                color: 'white',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.3)',
                },
              }}
            />
          )}
          <Button
            color="inherit"
            component={Link}
            to="/"
            startIcon={<ChatIcon />}
            sx={{ mr: 1 }}
          >
            Chat
          </Button>
          <Button
            color="inherit"
            component={Link}
            to="/about"
            startIcon={<InfoIcon />}
            sx={{ mr: 1 }}
          >
            About
          </Button>
          <Button
            color="inherit"
            component={Link}
            to="/admin"
            startIcon={<SettingsIcon />}
          >
            Admin
          </Button>
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ flexGrow: 1, py: 4 }}>
        {children}
      </Container>
      <Box
        component="footer"
        sx={{
          py: 2,
          px: 2,
          mt: 'auto',
          backgroundColor: (theme) =>
            theme.palette.mode === 'light'
              ? theme.palette.grey[200]
              : theme.palette.grey[800],
        }}
      >
        <Typography variant="body2" color="text.secondary" align="center">
          Adobe Experience League Chatbot (Unofficial) - Powered by AWS Bedrock
        </Typography>
      </Box>
    </Box>
  )
}

