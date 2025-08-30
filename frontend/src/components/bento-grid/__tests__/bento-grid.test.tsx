import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import { BentoGrid } from '../bento-grid'
import { BentoGridCard, CardType, CardSize } from '@/types/dashboard'

const mockCards: BentoGridCard[] = [
  {
    id: '1',
    cardType: CardType.KPI,
    size: CardSize.SMALL,
    position: { row: 0, col: 0 },
    content: {
      title: 'Revenue',
      value: '$2.4M',
      label: 'This Quarter',
      change: '+12.5%',
      trend: 'up'
    }
  },
  {
    id: '2',
    cardType: CardType.CHART,
    size: CardSize.MEDIUM_H,
    position: { row: 0, col: 1 },
    content: {
      title: 'Cash Flow',
      chartType: 'Line Chart',
      description: 'Monthly trends'
    }
  }
]

const mockOnCardsUpdate = vi.fn()

describe('BentoGrid', () => {
  beforeEach(() => {
    mockOnCardsUpdate.mockClear()
  })

  it('renders cards correctly', () => {
    render(<BentoGrid cards={mockCards} onCardsUpdate={mockOnCardsUpdate} />)

    expect(screen.getByText('Revenue')).toBeInTheDocument()
    expect(screen.getByText('$2.4M')).toBeInTheDocument()
    expect(screen.getByText('Cash Flow')).toBeInTheDocument()
  })

  it('applies correct grid classes for different card sizes', () => {
    render(<BentoGrid cards={mockCards} onCardsUpdate={mockOnCardsUpdate} />)

    // Check if the grid container has responsive classes
    const gridContainer = screen.getByText('Revenue').closest('.grid')
    expect(gridContainer).toHaveClass('grid-cols-2', 'md:grid-cols-4', 'lg:grid-cols-6')
  })

  it('renders drag handles for draggable cards', () => {
    render(<BentoGrid cards={mockCards} onCardsUpdate={mockOnCardsUpdate} />)

    // Should have grip handles for dragging
    const gripHandles = document.querySelectorAll('[data-testid="grip-handle"]')
    expect(gripHandles.length).toBeGreaterThan(0)
  })

  it('handles empty cards array', () => {
    render(<BentoGrid cards={[]} onCardsUpdate={mockOnCardsUpdate} />)

    // Should render without crashing
    const gridContainer = document.querySelector('.grid')
    expect(gridContainer).toBeInTheDocument()
  })
})