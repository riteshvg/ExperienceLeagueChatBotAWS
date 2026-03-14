import { Box, Paper, Typography, Chip, Link, List, ListItem, ListItemText } from '@mui/material'
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import VideoLibraryIcon from '@mui/icons-material/VideoLibrary'

interface SourceLink {
  title: string
  url: string
  video_url?: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  metadata?: {
    model_used?: string
    documents?: any[]
    source_links?: SourceLink[]
  }
}

interface ChatMessageProps {
  message: Message
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
      }}
    >
      <Paper
        sx={{
          p: 2,
          maxWidth: '70%',
          backgroundColor: isUser ? 'primary.light' : 'grey.100',
          color: isUser ? 'primary.contrastText' : 'text.primary',
        }}
      >
        <Typography variant="body2" sx={{ mb: 1, fontWeight: 'bold' }}>
          {isUser ? '👤 You' : '🤖 Assistant'}
        </Typography>
        <ReactMarkdown rehypePlugins={[rehypeRaw]}>
          {message.content}
        </ReactMarkdown>
        
        {/* Source Links */}
        {!isUser && message.metadata?.source_links && message.metadata.source_links.length > 0 && (
          <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
            <Typography variant="caption" sx={{ fontWeight: 'bold', display: 'block', mb: 1 }}>
              📚 Related Articles:
            </Typography>
            <List dense sx={{ py: 0 }}>
              {message.metadata.source_links.map((link, index) => (
                <ListItem key={index} sx={{ px: 0, py: 0.5, flexDirection: 'column', alignItems: 'flex-start' }}>
                  <Link
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      textDecoration: 'none',
                      color: 'primary.main',
                      mb: link.video_url ? 0.5 : 0,
                      '&:hover': {
                        textDecoration: 'underline',
                      },
                    }}
                  >
                    <Typography variant="body2" sx={{ mr: 0.5 }}>
                      {link.title}
                    </Typography>
                    <OpenInNewIcon sx={{ fontSize: 14, ml: 0.5 }} />
                  </Link>
                  {link.video_url && (
                    <Link
                      href={link.video_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        textDecoration: 'none',
                        color: 'secondary.main',
                        fontSize: '0.75rem',
                        ml: 1,
                        '&:hover': {
                          textDecoration: 'underline',
                        },
                      }}
                    >
                      <VideoLibraryIcon sx={{ fontSize: 14, mr: 0.5 }} />
                      <Typography variant="caption">
                        Watch Video
                      </Typography>
                      <OpenInNewIcon sx={{ fontSize: 12, ml: 0.5 }} />
                    </Link>
                  )}
                </ListItem>
              ))}
            </List>
          </Box>
        )}
        
        {message.metadata?.model_used && (
          <Chip
            label={`Model: ${message.metadata.model_used}`}
            size="small"
            sx={{ mt: 1 }}
          />
        )}
        <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.7 }}>
          {message.timestamp.toLocaleTimeString()}
        </Typography>
      </Paper>
    </Box>
  )
}

