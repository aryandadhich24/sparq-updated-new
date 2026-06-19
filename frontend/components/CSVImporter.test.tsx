import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { CSVImporter } from './CSVImporter'

// Mock papaparse so tests don't depend on the real CSV parser
vi.mock('papaparse', () => ({
    __esModule: true,
    default: {
        parse: vi.fn(),
    },
}))

import Papa from 'papaparse'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createMockFile(name = 'test.csv', content = 'a,b\n1,2'): File {
    return new File([content], name, { type: 'text/csv' })
}

/** Simulate PapaParse calling its `complete` callback with the given fields/data. */
function simulatePapaParse(fields: string[], data: Record<string, string>[]) {
    ;(Papa.parse as ReturnType<typeof vi.fn>).mockImplementation(
        (_file: File, opts: { header: boolean; preview?: number; complete: (r: any) => void }) => {
            opts.complete({ meta: { fields }, data })
        },
    )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('CSVImporter', () => {
    const mockOnImport = vi.fn()

    beforeEach(() => {
        vi.clearAllMocks()
        mockOnImport.mockResolvedValue({ message: 'Imported 2 rows', errors: [] })
    })

    // ----- Initial render -----

    it('renders the upload interface with correct title for DECISION type', () => {
        render(<CSVImporter type="DECISION" onImport={mockOnImport} />)

        expect(screen.getByText('Import Decisions')).toBeInTheDocument()
        expect(screen.getByText('Click to upload CSV')).toBeInTheDocument()
    })

    it('renders the upload interface with correct title for OUTCOME type', () => {
        render(<CSVImporter type="OUTCOME" onImport={mockOnImport} />)

        expect(screen.getByText('Import Outcomes')).toBeInTheDocument()
    })

    it('has a hidden file input that accepts .csv', () => {
        render(<CSVImporter type="DECISION" onImport={mockOnImport} />)

        const input = document.getElementById('csv-upload') as HTMLInputElement
        expect(input).not.toBeNull()
        expect(input.type).toBe('file')
        expect(input.accept).toBe('.csv')
    })

    // ----- File selection & preview -----

    it('shows file name and preview table after selecting a file', async () => {
        const fields = ['description', 'decision_type', 'start_date', 'cost']
        const data = [
            { description: 'Ad Run', decision_type: 'AD_CAMPAIGN', start_date: '2026-01-01', cost: '500' },
        ]
        simulatePapaParse(fields, data)

        render(<CSVImporter type="DECISION" onImport={mockOnImport} />)

        const input = document.getElementById('csv-upload') as HTMLInputElement
        fireEvent.change(input, { target: { files: [createMockFile()] } })

        await waitFor(() => {
            expect(screen.getByText('test.csv')).toBeInTheDocument()
        })

        // Column headers from CSV should appear in preview table
        expect(screen.getByText('description')).toBeInTheDocument()
        expect(screen.getByText('Previewing first 5 rows')).toBeInTheDocument()
    })

    it('shows column mapping selects after file is parsed', async () => {
        const fields = ['description', 'cost']
        simulatePapaParse(fields, [{ description: 'test', cost: '100' }])

        render(<CSVImporter type="DECISION" onImport={mockOnImport} />)

        const input = document.getElementById('csv-upload') as HTMLInputElement
        fireEvent.change(input, { target: { files: [createMockFile()] } })

        await waitFor(() => {
            expect(screen.getByText('Map Columns')).toBeInTheDocument()
        })

        // The schema fields for DECISION type should appear as labels
        expect(screen.getByText('Description (Required)')).toBeInTheDocument()
        expect(screen.getByText('Cost')).toBeInTheDocument()
    })

    it('shows the Run Import button after file selection', async () => {
        simulatePapaParse(['col1'], [{ col1: 'val' }])

        render(<CSVImporter type="DECISION" onImport={mockOnImport} />)

        const input = document.getElementById('csv-upload') as HTMLInputElement
        fireEvent.change(input, { target: { files: [createMockFile()] } })

        await waitFor(() => {
            expect(screen.getByText('Run Import')).toBeInTheDocument()
        })
    })

    // ----- Remove file -----

    it('returns to upload interface when Remove button is clicked', async () => {
        simulatePapaParse(['col1'], [{ col1: 'val' }])

        render(<CSVImporter type="DECISION" onImport={mockOnImport} />)

        const input = document.getElementById('csv-upload') as HTMLInputElement
        fireEvent.change(input, { target: { files: [createMockFile()] } })

        await waitFor(() => {
            expect(screen.getByText('test.csv')).toBeInTheDocument()
        })

        fireEvent.click(screen.getByText('Remove'))

        await waitFor(() => {
            expect(screen.getByText('Click to upload CSV')).toBeInTheDocument()
        })
    })

    // ----- Import execution -----

    it('calls onImport with mapped data when Run Import is clicked', async () => {
        const fields = ['description', 'decision_type', 'start_date', 'cost']
        const previewData = [
            { description: 'Ad Run', decision_type: 'AD_CAMPAIGN', start_date: '2026-01-01', cost: '500' },
        ]
        // First call for preview, second call for actual import
        let callCount = 0
        ;(Papa.parse as ReturnType<typeof vi.fn>).mockImplementation(
            (_file: File, opts: { header: boolean; preview?: number; complete: (r: any) => void }) => {
                callCount++
                if (callCount === 1) {
                    // Preview parse
                    opts.complete({ meta: { fields }, data: previewData })
                } else {
                    // Full parse for import
                    opts.complete({ meta: { fields }, data: previewData })
                }
            },
        )

        render(<CSVImporter type="DECISION" onImport={mockOnImport} />)

        const input = document.getElementById('csv-upload') as HTMLInputElement
        fireEvent.change(input, { target: { files: [createMockFile()] } })

        await waitFor(() => {
            expect(screen.getByText('Run Import')).toBeInTheDocument()
        })

        fireEvent.click(screen.getByText('Run Import'))

        await waitFor(() => {
            expect(mockOnImport).toHaveBeenCalledTimes(1)
        })

        // Verify the data passed to onImport contains the mapped fields
        const importedData = mockOnImport.mock.calls[0][0]
        expect(importedData[0]).toHaveProperty('description', 'Ad Run')
        expect(importedData[0]).toHaveProperty('cost', 500) // parsed as float
    })

    it('shows result message after import completes', async () => {
        const fields = ['description', 'decision_type', 'start_date', 'cost']
        const data = [
            { description: 'Campaign X', decision_type: 'AD_CAMPAIGN', start_date: '2026-06-01', cost: '200' },
        ]
        ;(Papa.parse as ReturnType<typeof vi.fn>).mockImplementation(
            (_file: File, opts: any) => {
                opts.complete({ meta: { fields }, data })
            },
        )

        render(<CSVImporter type="DECISION" onImport={mockOnImport} />)

        const input = document.getElementById('csv-upload') as HTMLInputElement
        fireEvent.change(input, { target: { files: [createMockFile()] } })

        await waitFor(() => {
            expect(screen.getByText('Run Import')).toBeInTheDocument()
        })

        fireEvent.click(screen.getByText('Run Import'))

        await waitFor(() => {
            expect(screen.getByText('Imported 2 rows')).toBeInTheDocument()
        })

        // The "Import Another File" button should appear
        expect(screen.getByText('Import Another File')).toBeInTheDocument()
    })

    it('shows Import Another File button that resets the form', async () => {
        const fields = ['description', 'decision_type', 'start_date', 'cost']
        const data = [
            { description: 'Test', decision_type: 'HIRE', start_date: '2026-01-01', cost: '100' },
        ]
        ;(Papa.parse as ReturnType<typeof vi.fn>).mockImplementation(
            (_file: File, opts: any) => {
                opts.complete({ meta: { fields }, data })
            },
        )

        render(<CSVImporter type="DECISION" onImport={mockOnImport} />)

        const input = document.getElementById('csv-upload') as HTMLInputElement
        fireEvent.change(input, { target: { files: [createMockFile()] } })

        await waitFor(() => screen.getByText('Run Import'))
        fireEvent.click(screen.getByText('Run Import'))

        await waitFor(() => screen.getByText('Import Another File'))
        fireEvent.click(screen.getByText('Import Another File'))

        await waitFor(() => {
            expect(screen.getByText('Click to upload CSV')).toBeInTheDocument()
        })
    })

    // ----- Error display -----

    it('shows error list when import has errors', async () => {
        mockOnImport.mockResolvedValue({
            message: 'Imported with errors',
            errors: ['Row 3: missing cost'],
        })

        const fields = ['description', 'decision_type', 'start_date', 'cost']
        const data = [
            { description: 'Valid', decision_type: 'TOOL', start_date: '2026-01-01', cost: '50' },
        ]
        ;(Papa.parse as ReturnType<typeof vi.fn>).mockImplementation(
            (_file: File, opts: any) => {
                opts.complete({ meta: { fields }, data })
            },
        )

        render(<CSVImporter type="DECISION" onImport={mockOnImport} />)

        const input = document.getElementById('csv-upload') as HTMLInputElement
        fireEvent.change(input, { target: { files: [createMockFile()] } })

        await waitFor(() => screen.getByText('Run Import'))
        fireEvent.click(screen.getByText('Run Import'))

        await waitFor(() => {
            expect(screen.getByText('Imported with errors')).toBeInTheDocument()
            expect(screen.getByText('Errors:')).toBeInTheDocument()
            expect(screen.getByText('Row 3: missing cost')).toBeInTheDocument()
        })
    })

    // ----- OUTCOME type fields -----

    it('shows correct schema fields for OUTCOME type', async () => {
        simulatePapaParse(['value', 'date'], [{ value: '100', date: '2026-01-01' }])

        render(<CSVImporter type="OUTCOME" onImport={mockOnImport} />)

        const input = document.getElementById('csv-upload') as HTMLInputElement
        fireEvent.change(input, { target: { files: [createMockFile()] } })

        await waitFor(() => {
            expect(screen.getByText('Map Columns')).toBeInTheDocument()
        })

        // OUTCOME-specific labels
        expect(screen.getByText('Description')).toBeInTheDocument()
        expect(screen.getByText('Value')).toBeInTheDocument()
        expect(screen.getByText('Date (YYYY-MM-DD)')).toBeInTheDocument()
    })
})
