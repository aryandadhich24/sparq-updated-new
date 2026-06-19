import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

describe('Test infrastructure', () => {
    it('renders a React element in jsdom', () => {
        render(<div>Hello SparqAI</div>)
        expect(screen.getByText('Hello SparqAI')).toBeInTheDocument()
    })

    it('jest-dom matchers are available', () => {
        render(<button disabled>Click me</button>)
        expect(screen.getByRole('button')).toBeDisabled()
    })

    it('can query by role', () => {
        render(
            <form>
                <label htmlFor="email">Email</label>
                <input id="email" type="email" placeholder="you@example.com" />
            </form>,
        )
        expect(screen.getByRole('textbox')).toHaveAttribute('placeholder', 'you@example.com')
    })

    it('supports queryByText returning null for missing text', () => {
        render(<p>Exists</p>)
        expect(screen.queryByText('Does not exist')).not.toBeInTheDocument()
    })
})
