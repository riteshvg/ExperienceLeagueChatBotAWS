import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider } from '@mui/material/styles'
import { theme } from '../theme'
import ChatPage from '../pages/ChatPage'
import * as api from '../services/api'

vi.mock('../services/api')

describe('ChatPage', () => {
  const renderChatPage = () => {
    return render(
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          <ChatPage />
        </ThemeProvider>
      </BrowserRouter>
    )
  }

  it('renders chat interface', () => {
    renderChatPage()
    expect(screen.getByText(/Chat/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Ask your question/i)).toBeInTheDocument()
  })

  it('displays empty state when no messages', () => {
    renderChatPage()
    expect(screen.getByText(/No messages yet/i)).toBeInTheDocument()
  })

  it('handles form submission', async () => {
    const mockResponse = {
      success: true,
      answer: 'Test answer',
      model_used: 'haiku',
    }

    vi.mocked(api.chatApi.sendMessage).mockResolvedValue(mockResponse)

    renderChatPage()

    const input = screen.getByPlaceholderText(/Ask your question/i)
    const button = screen.getByRole('button', { name: /Send/i })

    // Type query
    input.setAttribute('value', 'Test question')
    
    // Submit form
    button.click()

    await waitFor(() => {
      expect(api.chatApi.sendMessage).toHaveBeenCalled()
    })
  })
})

