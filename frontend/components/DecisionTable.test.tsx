import { render, screen, within } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { DecisionTable } from './DecisionTable'
import type { Decision } from '@/lib/types'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockDecisions: Decision[] = [
    {
        id: 1,
        description: 'Google Ads Q1',
        type: 'AD_CAMPAIGN',
        status: 'ACTIVE',
        start_date: '2026-01-15',
        cost: 5000,
        total_cost: 5000,
        roi: 3.20,
        value: 16000,
        confidence: 0.85,
        action: 'SCALE',
        source: 'CSV',
        details: 'Google campaign details',
    },
    {
        id: 2,
        description: 'Senior Dev Hire',
        type: 'HIRE',
        status: 'ACTIVE',
        start_date: '2026-02-01',
        cost: 12000,
        total_cost: 12000,
        roi: 0.60,
        value: 7200,
        confidence: 0.45,
        action: 'KILL',
        source: 'Manual',
        details: 'Engineering hire',
    },
    {
        id: 3,
        description: 'CRM Tool',
        type: 'TOOL',
        status: 'ACTIVE',
        start_date: '2026-03-01',
        cost: 800,
        total_cost: 800,
        roi: 1.50,
        value: 1200,
        confidence: 0.60,
        action: 'MAINTAIN',
        source: 'CSV',
        details: 'Tooling subscription',
    },
    {
        id: 4,
        description: 'Design Agency',
        type: 'VENDOR',
        status: 'ACTIVE',
        start_date: '2026-03-10',
        cost: 3000,
        total_cost: 3000,
        roi: 2.00,
        value: 6000,
        confidence: 0.72,
        action: 'INVESTIGATE',
        source: 'Manual',
        details: 'Vendor contract',
    },
]

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('DecisionTable', () => {
    // ----- Rendering with data -----

    it('renders a table row for each decision', () => {
        render(<DecisionTable decisions={mockDecisions} />)

        expect(screen.getByText('Google Ads Q1')).toBeInTheDocument()
        expect(screen.getByText('Senior Dev Hire')).toBeInTheDocument()
        expect(screen.getByText('CRM Tool')).toBeInTheDocument()
        expect(screen.getByText('Design Agency')).toBeInTheDocument()
    })

    it('renders all table column headers', () => {
        render(<DecisionTable decisions={mockDecisions} />)

        expect(screen.getByText('Decision')).toBeInTheDocument()
        expect(screen.getByText('Type')).toBeInTheDocument()
        expect(screen.getByText('Total Cost')).toBeInTheDocument()
        expect(screen.getByText('Attributed Value')).toBeInTheDocument()
        expect(screen.getByText('ROI')).toBeInTheDocument()
        expect(screen.getByText('Confidence')).toBeInTheDocument()
        expect(screen.getByText('Action')).toBeInTheDocument()
    })

    it('formats ROI values with x suffix', () => {
        render(<DecisionTable decisions={mockDecisions} />)

        expect(screen.getByText('3.20x')).toBeInTheDocument()
        expect(screen.getByText('0.60x')).toBeInTheDocument()
        expect(screen.getByText('1.50x')).toBeInTheDocument()
    })

    it('formats currency values with $ and commas', () => {
        render(<DecisionTable decisions={mockDecisions} />)

        expect(screen.getByText('$16,000')).toBeInTheDocument()
        expect(screen.getByText('$5,000')).toBeInTheDocument()
        expect(screen.getByText('$12,000')).toBeInTheDocument()
    })

    it('displays confidence as percentage', () => {
        render(<DecisionTable decisions={mockDecisions} />)

        expect(screen.getByText('85%')).toBeInTheDocument()
        expect(screen.getByText('45%')).toBeInTheDocument()
        expect(screen.getByText('60%')).toBeInTheDocument()
    })

    it('renders action badges for each action type', () => {
        render(<DecisionTable decisions={mockDecisions} />)

        expect(screen.getByText('SCALE')).toBeInTheDocument()
        expect(screen.getByText('KILL')).toBeInTheDocument()
        expect(screen.getByText('MAINTAIN')).toBeInTheDocument()
        expect(screen.getByText('INVESTIGATE')).toBeInTheDocument()
    })

    it('renders type badges for each decision type', () => {
        render(<DecisionTable decisions={mockDecisions} />)

        expect(screen.getByText('AD CAMPAIGN')).toBeInTheDocument()
        expect(screen.getByText('HIRE')).toBeInTheDocument()
        expect(screen.getByText('TOOL')).toBeInTheDocument()
        expect(screen.getByText('VENDOR')).toBeInTheDocument()
    })

    // ----- Empty state -----

    it('shows empty state message when decisions array is empty', () => {
        render(<DecisionTable decisions={[]} />)

        expect(screen.getByText('No decisions yet.')).toBeInTheDocument()
        expect(screen.getByText('Seed demo data to get started.')).toBeInTheDocument()
    })

    it('does not render a table element in empty state', () => {
        render(<DecisionTable decisions={[]} />)

        expect(screen.queryByRole('table')).not.toBeInTheDocument()
    })

    // ----- Links / navigation -----

    it('renders each decision description as a link to its detail page', () => {
        render(<DecisionTable decisions={mockDecisions} />)

        const link1 = screen.getByText('Google Ads Q1').closest('a')
        const link2 = screen.getByText('Senior Dev Hire').closest('a')

        expect(link1).toHaveAttribute('href', '/decisions/1')
        expect(link2).toHaveAttribute('href', '/decisions/2')
    })

    // ----- Correct number of rows -----

    it('renders the correct number of body rows', () => {
        render(<DecisionTable decisions={mockDecisions} />)

        const table = screen.getByRole('table')
        const tbody = table.querySelector('tbody')!
        const rows = within(tbody).getAllByRole('row')

        expect(rows).toHaveLength(mockDecisions.length)
    })

    // ----- Single decision -----

    it('renders correctly with a single decision', () => {
        render(<DecisionTable decisions={[mockDecisions[0]]} />)

        expect(screen.getByText('Google Ads Q1')).toBeInTheDocument()
        expect(screen.queryByText('Senior Dev Hire')).not.toBeInTheDocument()
    })
})
