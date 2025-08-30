import { render, screen } from '@testing-library/react'
import { DndContext } from '@dnd-kit/core'
import { DraggableCard } from '../draggable-card'
import { BentoGridCard, CardType, CardSize } from '@/types/dashboard'

const mockKPICard: BentoGridCard = {
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
}

const mockTableCard: BentoGridCard = {
  id: '2',
  cardType: CardType.TABLE,
  size: CardSize.LARGE,
  position: { row: 0, col: 1 },
  content: {
    title: 'Top Investments',
    headers: ['Investment', 'ROI'],
    rows: [
      ['Tech Upgrade', '18.5%'],
      ['Market Expansion', '12.3%']
    ]
  }
}

const mockInsightCard: BentoGridCard = {
  id: '3',
  cardType: CardType.INSIGHT,
  size: CardSize.MEDIUM_V,
  position: { row: 1, col: 0 },
  content: {
    title: 'Budget Alert',
    description: 'Marketing department is over budget'
  }
}

const renderWithDndContext = (card: BentoGridCard) => {
  return render(
    <DndContext>
      <DraggableCard card={card} />
    </DndContext>
  )
}

describe('DraggableCard', () => {
  it('renders KPI card correctly', () => {
    renderWithDndContext(mockKPICard)

    expect(screen.getByText('Revenue')).toBeInTheDocument()
    expect(screen.getByText('$2.4M')).toBeInTheDocument()
    expect(screen.getByText('+12.5%')).toBeInTheDocument()
  })

  it('renders table card correctly', () => {
    renderWithDndContext(mockTableCard)

    expect(screen.getByText('Top Investments')).toBeInTheDocument()
    expect(screen.getByText('Investment')).toBeInTheDocument()
    expect(screen.getByText('ROI')).toBeInTheDocument()
    expect(screen.getByText('Tech Upgrade')).toBeInTheDocument()
    expect(screen.getByText('18.5%')).toBeInTheDocument()
  })

  it('renders insight card correctly', () => {
    renderWithDndContext(mockInsightCard)

    expect(screen.getAllByText('Budget Alert')).toHaveLength(2) // Title appears in both card header and alert
    expect(screen.getByText('Marketing department is over budget')).toBeInTheDocument()
  })

  it('shows drag handle for draggable cards', () => {
    renderWithDndContext(mockKPICard)

    // Should have a grip icon for dragging
    const gripIcon = document.querySelector('svg')
    expect(gripIcon).toBeInTheDocument()
  })

  it('handles chart card type', () => {
    const chartCard: BentoGridCard = {
      id: '4',
      cardType: CardType.CHART,
      size: CardSize.MEDIUM_H,
      position: { row: 0, col: 0 },
      content: {
        title: 'Cash Flow',
        chartType: 'Line Chart',
        description: 'Monthly trends'
      }
    }

    renderWithDndContext(chartCard)

    expect(screen.getByText('Cash Flow')).toBeInTheDocument()
    expect(screen.getByText('Chart: Line Chart')).toBeInTheDocument()
    expect(screen.getByText('Monthly trends')).toBeInTheDocument()
  })
})