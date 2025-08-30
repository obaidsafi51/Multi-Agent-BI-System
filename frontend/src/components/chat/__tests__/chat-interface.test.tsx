import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { ChatInterface } from '../chat-interface'
import { ChatMessage, QuerySuggestion } from '@/types/dashboard'

const mockMessages: ChatMessage[] = [
  {
    id: '1',
    content: 'Hello, how can I help you?',
    sender: 'assistant',
    timestamp: new Date(),
  },
]

const mockSuggestions: QuerySuggestion[] = [
  {
    id: '1',
    text: 'Show me revenue trends',
    category: 'Revenue',
    confidence: 0.9,
  },
]

const mockOnSendMessage = vi.fn()

describe('ChatInterface', () => {
  beforeEach(() => {
    mockOnSendMessage.mockClear()
  })

  it('renders chat messages correctly', () => {
    render(
      <ChatInterface
        messages={mockMessages}
        suggestions={mockSuggestions}
        onSendMessage={mockOnSendMessage}
      />
    )

    expect(screen.getByText('Hello, how can I help you?')).toBeInTheDocument()
    expect(screen.getByText('AI CFO Assistant')).toBeInTheDocument()
  })

  it('allows user to send messages', async () => {
    const user = userEvent.setup()
    render(
      <ChatInterface
        messages={mockMessages}
        suggestions={mockSuggestions}
        onSendMessage={mockOnSendMessage}
      />
    )

    const input = screen.getByPlaceholderText('Ask about your financial data...')
    const sendButton = screen.getByRole('button', { name: /send message/i })

    await user.type(input, 'What is my revenue?')
    await user.click(sendButton)

    expect(mockOnSendMessage).toHaveBeenCalledWith('What is my revenue?')
  })

  it('shows suggestions when toggled', async () => {
    const user = userEvent.setup()
    render(
      <ChatInterface
        messages={mockMessages}
        suggestions={mockSuggestions}
        onSendMessage={mockOnSendMessage}
      />
    )

    const showSuggestionsButton = screen.getByText('Show Suggestions')
    await user.click(showSuggestionsButton)

    expect(screen.getByText('Show me revenue trends')).toBeInTheDocument()
  })

  it('handles suggestion clicks', async () => {
    const user = userEvent.setup()
    render(
      <ChatInterface
        messages={mockMessages}
        suggestions={mockSuggestions}
        onSendMessage={mockOnSendMessage}
      />
    )

    // Show suggestions first
    const showSuggestionsButton = screen.getByText('Show Suggestions')
    await user.click(showSuggestionsButton)

    // Click on a suggestion
    const suggestion = screen.getByText('Show me revenue trends')
    await user.click(suggestion)

    // Check if input is populated
    const input = screen.getByPlaceholderText('Ask about your financial data...')
    expect(input).toHaveValue('Show me revenue trends')
  })

  it('disables send button when input is empty', () => {
    render(
      <ChatInterface
        messages={mockMessages}
        suggestions={mockSuggestions}
        onSendMessage={mockOnSendMessage}
      />
    )

    const sendButton = screen.getByRole('button', { name: /send message/i })
    expect(sendButton).toBeDisabled()
  })

  it('shows feedback buttons for assistant messages', () => {
    render(
      <ChatInterface
        messages={mockMessages}
        suggestions={mockSuggestions}
        onSendMessage={mockOnSendMessage}
      />
    )

    // Should have thumbs up and thumbs down buttons
    expect(screen.getByRole('button', { name: /thumbs up/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /thumbs down/i })).toBeInTheDocument()
  })
})