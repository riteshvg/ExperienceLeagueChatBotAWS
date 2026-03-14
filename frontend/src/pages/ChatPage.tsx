import { useState, useRef, useEffect } from 'react'
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Alert,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import { useChatStore } from '../store/chatStore'
import ChatMessage from '../components/ChatMessage'

export default function ChatPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [streamingMessage, setStreamingMessage] = useState<string>('')
  const [streamingMetadata, setStreamingMetadata] = useState<any>(null)
  const { messages, addMessage, sessionId, setSessionId } = useChatStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

  // Initialize session ID if not set
  useEffect(() => {
    if (!sessionId) {
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      setSessionId(newSessionId)
    }
  }, [sessionId, setSessionId])

  // Initialize session ID if not set
  useEffect(() => {
    if (!sessionId) {
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      setSessionId(newSessionId)
    }
  }, [sessionId, setSessionId])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingMessage])

  // Fallback function for HTTP request if WebSocket fails
  const fallbackToHttpRequest = async (message: string) => {
    try {
      console.log('Falling back to HTTP request')
      const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: message,
          user_id: 'anonymous',
          session_id: sessionId,
        }),
      })

      const data = await response.json()

      if (data.success && data.answer) {
        // Simulate typing effect for HTTP response
        const answer = data.answer
        let displayedText = ''
        
        for (let i = 0; i < answer.length; i++) {
          displayedText += answer[i]
          setStreamingMessage(displayedText)
          await new Promise(resolve => setTimeout(resolve, 10)) // 10ms delay per character
        }

        // Save complete message
        addMessage({
          role: 'assistant',
          content: answer,
          timestamp: new Date(),
          metadata: {
            model_used: data.model_used,
            documents: data.documents || [],
            source_links: data.source_links || [],
          },
        })
        setStreamingMessage('')
        setStreamingMetadata(null)
      } else {
        setError(data.error || 'Failed to get response')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault()
    }
    if (!query.trim() || loading) return

    const userMessage = query.trim()
    setQuery('')
    setError(null)
    setLoading(true)
    setStreamingMessage('')
    setStreamingMetadata(null)

    // Add user message
    addMessage({
      role: 'user',
      content: userMessage,
      timestamp: new Date(),
    })

    try {
      // Construct WebSocket URL
      let wsUrl: string
      if (API_BASE_URL.startsWith('http://')) {
        wsUrl = API_BASE_URL.replace('http://', 'ws://') + '/api/v1/chat/stream'
      } else if (API_BASE_URL.startsWith('https://')) {
        wsUrl = API_BASE_URL.replace('https://', 'wss://') + '/api/v1/chat/stream'
      } else {
        // Default to ws://localhost:8000
        wsUrl = `ws://localhost:8000/api/v1/chat/stream`
      }
      
      console.log('Connecting to WebSocket:', wsUrl)
      
      const ws = new WebSocket(wsUrl)
      let fullAnswer = ''
      let receivedMetadata: any = null
      let connectionTimeout: ReturnType<typeof setTimeout>

      // Set connection timeout
      connectionTimeout = setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          console.error('WebSocket connection timeout')
          ws.close()
          // Fallback to regular HTTP request
          fallbackToHttpRequest(userMessage)
        }
      }, 5000)

      ws.onopen = () => {
        console.log('WebSocket connected')
        clearTimeout(connectionTimeout)
        ws.send(JSON.stringify({
          query: userMessage,
          user_id: 'anonymous',
          session_id: sessionId,
        }))
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.error) {
            setError(data.error)
            setLoading(false)
            ws.close()
            return
          }

          if (data.chunk) {
            fullAnswer += data.chunk
            setStreamingMessage(fullAnswer)
          }

          // Store metadata from chunks (update if we get source_links)
          if (data.model_used || data.source_links) {
            receivedMetadata = {
              model_used: data.model_used || receivedMetadata?.model_used,
              documents: data.documents || receivedMetadata?.documents || [],
              source_links: data.source_links || receivedMetadata?.source_links || [],
            }
            setStreamingMetadata(receivedMetadata)
          }

          if (data.is_complete) {
            // Save the complete message
            addMessage({
              role: 'assistant',
              content: fullAnswer,
              timestamp: new Date(),
              metadata: receivedMetadata || {
                model_used: data.model_used,
                documents: data.documents || [],
                source_links: data.source_links || [],
              },
            })
            setStreamingMessage('')
            setStreamingMetadata(null)
            setLoading(false)
            ws.close()
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err)
        }
      }

      ws.onerror = (err) => {
        console.error('WebSocket error:', err)
        clearTimeout(connectionTimeout)
        // Fallback to regular HTTP request
        fallbackToHttpRequest(userMessage)
      }

      ws.onclose = (event) => {
        clearTimeout(connectionTimeout)
        if (loading && !fullAnswer && event.code !== 1000) {
          // Connection closed unexpectedly, try HTTP fallback
          if (ws.readyState === WebSocket.CLOSED) {
            fallbackToHttpRequest(userMessage)
          }
        }
      }

    } catch (err) {
      console.error('WebSocket setup error:', err)
      // Fallback to regular HTTP request
      fallbackToHttpRequest(userMessage)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    // Submit on Enter (but allow Shift+Enter for new line)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        💬 Chat
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Ask questions about Adobe Analytics, Customer Journey Analytics, and Adobe Experience Platform
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 2, minHeight: '400px', maxHeight: '600px', overflow: 'auto' }}>
        {messages.length === 0 && !streamingMessage ? (
          <Typography variant="body2" color="text.secondary" align="center">
            No messages yet. Ask a question to start the conversation!
          </Typography>
        ) : (
          <>
            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}
            {streamingMessage && (
              <ChatMessage
                message={{
                  role: 'assistant',
                  content: streamingMessage,
                  timestamp: new Date(),
                  metadata: streamingMetadata,
                }}
              />
            )}
          </>
        )}
        {loading && !streamingMessage && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Paper>

      <Paper component="form" onSubmit={handleSubmit} sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask your question about Adobe Analytics, Customer Journey Analytics related topics... (Press Enter to send, Shift+Enter for new line)"
            disabled={loading}
          />
          <Button
            type="submit"
            variant="contained"
            endIcon={<SendIcon />}
            disabled={loading || !query.trim()}
            sx={{ minWidth: '100px' }}
          >
            {loading ? 'Sending...' : 'Send'}
          </Button>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
          {query.length}/20000 characters
        </Typography>
      </Paper>
    </Box>
  )
}

