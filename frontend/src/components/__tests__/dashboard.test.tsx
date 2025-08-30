import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import { Dashboard } from '../dashboard'

// Mock the child components
vi.mock('../chat/chat-interface', () => ({
  ChatInterface: ({ onSendMessage }: { onSendMessage: (content: string) => void }) => (
    <div data-testid="chat-interface">
      <button onClick={() => onSendMessage('test message')}>Send Test Message</button>
    </div>
  )
}))

vi.mock('../bento-grid/bento-grid', () => ({
  BentoGrid: ({ cards, onCardsUpdate }: { cards: unknown[], onCardsUpdate: (cards: unknown[]) => void }) => (
    <div data-testid="bento-grid">
      <div>Cards: {cards.length}</div>
      <button onClick={() => onCardsUpdate([])}>Update Cards</button>
    </div>
  )
}))

describe('Dashboard', () => {
  it('renders split-screen layout correctly', () => {
    render(<Dashboard />)

    expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
    expect(screen.getByTestId('bento-grid')).toBeInTheDocument()
  })

  it('has correct layout proportions', () => {
    render(<Dashboard />)

    const chatContainer = screen.getByTestId('chat-interface').parentElement
    const dashboardContainer = screen.getByTestId('bento-grid').parentElement

    // Chat should be 30% width
    expect(chatContainer).toHaveClass('w-[30%]')
    // Dashboard should be flex-1 (remaining space)
    expect(dashboardContainer).toHaveClass('flex-1')
  })

  it('handles message sending', async () => {
    render(<Dashboard />)

    const sendButton = screen.getByText('Send Test Message')
    fireEvent.click(sendButton)

    // Should not crash and should handle the message
    expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
  })

  it('handles card updates', () => {
    render(<Dashboard />)

    const updateButton = screen.getByText('Update Cards')
    fireEvent.click(updateButton)

    // Should not crash and should handle the update
    expect(screen.getByTestId('bento-grid')).toBeInTheDocument()
  })

  it('displays initial mock data', () => {
    render(<Dashboard />)

    // Should show some cards initially
    expect(screen.getByText(/Cards:/)).toBeInTheDocument()
  })
})