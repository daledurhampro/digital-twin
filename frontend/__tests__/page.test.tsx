import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import Home from '../app/page'
import { fullName } from '../data/data'

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('renders the page heading and embeds the twin chat', () => {
  render(<Home />)
  expect(screen.getByRole('heading', { level: 1, name: 'AI Digital Twin' })).toBeDefined()
  expect(screen.getByPlaceholderText('Type your message...')).toBeDefined()
  expect(screen.getByText(`${fullName}'s AI Digital Twin`)).toBeDefined()
})
