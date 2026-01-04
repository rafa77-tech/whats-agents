import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

// Example component for testing
function ExampleButton({ label, onClick }: { label: string; onClick?: () => void }): JSX.Element {
  return (
    <button onClick={onClick} type="button">
      {label}
    </button>
  )
}

describe('ExampleButton', () => {
  it('renders with correct label', () => {
    render(<ExampleButton label="Click me" />)

    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn()
    const { user } = await import('@testing-library/user-event').then((m) => ({
      user: m.default.setup(),
    }))

    render(<ExampleButton label="Click me" onClick={handleClick} />)

    await user.click(screen.getByRole('button'))

    expect(handleClick).toHaveBeenCalledTimes(1)
  })
})

describe('Type Safety Examples', () => {
  it('demonstrates proper typing with unknown', () => {
    // Example of how to properly type external data
    const externalData: unknown = { name: 'Test', value: 42 }

    // Type guard
    function isValidData(data: unknown): data is { name: string; value: number } {
      return (
        typeof data === 'object' &&
        data !== null &&
        'name' in data &&
        'value' in data &&
        typeof data.name === 'string' &&
        typeof data.value === 'number'
      )
    }

    if (isValidData(externalData)) {
      // TypeScript now knows the type
      expect(externalData.name).toBe('Test')
      expect(externalData.value).toBe(42)
    }
  })

  it('demonstrates discriminated unions', () => {
    type LoadingState = { status: 'loading' }
    type SuccessState = { status: 'success'; data: string }
    type ErrorState = { status: 'error'; error: Error }
    type State = LoadingState | SuccessState | ErrorState

    function processState(state: State): string {
      switch (state.status) {
        case 'loading':
          return 'Loading...'
        case 'success':
          return state.data
        case 'error':
          return state.error.message
      }
    }

    expect(processState({ status: 'loading' })).toBe('Loading...')
    expect(processState({ status: 'success', data: 'Hello' })).toBe('Hello')
    expect(processState({ status: 'error', error: new Error('Oops') })).toBe('Oops')
  })
})
