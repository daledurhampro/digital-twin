import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Twin from '../components/twin'
import { fullName } from '../data/data'

type FetchMock = ReturnType<typeof vi.fn>

function jsonResponse(body: unknown, ok = true) {
  return { ok, json: async () => body }
}

// Route fetch calls: the avatar HEAD check vs. the /chat POST.
function mockFetch(chat: (body: { message: string; session_id?: string }) => unknown, avatarOk = false) {
  const fn: FetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === '/avatar.png') return { ok: avatarOk }
    return chat(JSON.parse(init!.body as string))
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

function chatCalls(fn: FetchMock) {
  return fn.mock.calls.filter(([url]) => String(url).endsWith('/chat'))
}

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('Twin', () => {
  test('shows the empty-state greeting with the configured name', async () => {
    mockFetch(() => jsonResponse({}))
    render(<Twin />)
    expect(screen.getByText(`AI version of ${fullName}`)).toBeDefined()
    expect(screen.getByText(`Hello! I'm a Digital Twin of ${fullName}.`)).toBeDefined()
  })

  test('shows the avatar image when /avatar.png exists', async () => {
    mockFetch(() => jsonResponse({}), true)
    render(<Twin />)
    expect(await screen.findByAltText('Digital Twin Avatar')).toBeDefined()
  })

  test('falls back to the icon when the avatar is missing', async () => {
    const fn = mockFetch(() => jsonResponse({}), false)
    render(<Twin />)
    await waitFor(() => expect(fn).toHaveBeenCalledWith('/avatar.png', { method: 'HEAD' }))
    expect(screen.queryByAltText('Digital Twin Avatar')).toBeNull()
  })

  test('send button is disabled for empty or whitespace input', async () => {
    mockFetch(() => jsonResponse({}))
    const user = userEvent.setup()
    render(<Twin />)
    const button = screen.getByRole('button')
    expect((button as HTMLButtonElement).disabled).toBe(true)
    await user.type(screen.getByPlaceholderText('Type your message...'), '   ')
    expect((button as HTMLButtonElement).disabled).toBe(true)
  })

  test('sends a message on Enter and renders the reply', async () => {
    const fn = mockFetch(() => jsonResponse({ response: 'Hi there!', session_id: 'abc' }))
    const user = userEvent.setup()
    render(<Twin />)

    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement
    await user.type(input, 'Hello{Enter}')

    expect(await screen.findByText('Hi there!')).toBeDefined()
    expect(screen.getByText('Hello')).toBeDefined()
    expect(input.value).toBe('')

    const calls = chatCalls(fn)
    expect(calls).toHaveLength(1)
    const [url, init] = calls[0]
    expect(url).toBe('http://localhost:8000/chat')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ message: 'Hello' })
  })

  test('sends a message via the button', async () => {
    const fn = mockFetch(() => jsonResponse({ response: 'Clicked reply', session_id: 'abc' }))
    const user = userEvent.setup()
    render(<Twin />)

    await user.type(screen.getByPlaceholderText('Type your message...'), 'Via button')
    await user.click(screen.getByRole('button'))

    expect(await screen.findByText('Clicked reply')).toBeDefined()
    expect(chatCalls(fn)).toHaveLength(1)
  })

  test('reuses the session id returned by the first reply', async () => {
    const fn = mockFetch(({ message }) =>
      jsonResponse({ response: `echo ${message}`, session_id: 'session-123' }),
    )
    const user = userEvent.setup()
    render(<Twin />)
    const input = screen.getByPlaceholderText('Type your message...')

    await user.type(input, 'first{Enter}')
    await screen.findByText('echo first')
    await user.type(input, 'second{Enter}')
    await screen.findByText('echo second')

    const bodies = chatCalls(fn).map(([, init]) => JSON.parse(init.body))
    expect(bodies[0].session_id).toBeUndefined()
    expect(bodies[1].session_id).toBe('session-123')
  })

  test('shows an error message when the API responds with an error', async () => {
    mockFetch(() => jsonResponse({}, false))
    const user = userEvent.setup()
    render(<Twin />)

    await user.type(screen.getByPlaceholderText('Type your message...'), 'Hello{Enter}')

    expect(await screen.findByText('Sorry, I encountered an error. Please try again.')).toBeDefined()
  })

  test('shows an error message when the request throws', async () => {
    mockFetch(() => {
      throw new Error('network down')
    })
    const user = userEvent.setup()
    render(<Twin />)

    await user.type(screen.getByPlaceholderText('Type your message...'), 'Hello{Enter}')

    expect(await screen.findByText('Sorry, I encountered an error. Please try again.')).toBeDefined()
  })

  test('disables the input while waiting for a reply', async () => {
    let resolve!: (v: unknown) => void
    mockFetch(() => new Promise((r) => (resolve = r)))
    const user = userEvent.setup()
    render(<Twin />)
    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement

    await user.type(input, 'Hello{Enter}')
    await waitFor(() => expect(input.disabled).toBe(true))

    resolve(jsonResponse({ response: 'done', session_id: 's' }))
    expect(await screen.findByText('done')).toBeDefined()
    expect(input.disabled).toBe(false)
  })
})
