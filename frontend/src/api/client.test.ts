import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, geocode } from './client'

function respond(body: string, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(body, { status })),
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('api client', () => {
  it('returns parsed JSON', async () => {
    respond('[{"label":"Denver, CO","lat":39.7,"lon":-105}]')
    expect(await geocode('denv')).toEqual([{ label: 'Denver, CO', lat: 39.7, lon: -105 }])
  })

  it('encodes the query', async () => {
    respond('[]')
    await geocode('St. Louis/MO')
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe('/api/geocode?q=St.%20Louis%2FMO')
  })

  it('uses the server error message', async () => {
    respond('{"error":{"code":"NO_ROUTE","message":"No truck route."}}', 422)
    await expect(geocode('x')).rejects.toMatchObject({
      code: 'NO_ROUTE',
      message: 'No truck route.',
    })
  })

  it('handles an HTML error page', async () => {
    respond('<html>Bad gateway</html>', 502)
    await expect(geocode('x')).rejects.toMatchObject({ code: 'HTTP_502', status: 502 })
  })

  it('rejects an HTML page sent with 200', async () => {
    respond('<!doctype html><html></html>')
    await expect(geocode('x')).rejects.toMatchObject({ code: 'BAD_RESPONSE' })
  })

  it('turns a network failure into a friendly error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))),
    )
    const err = await geocode('x').catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.code).toBe('NETWORK')
  })

  it('lets an abort through untouched', async () => {
    const ctrl = new AbortController()
    ctrl.abort()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Promise.reject(new DOMException('Aborted', 'AbortError'))),
    )
    await expect(geocode('x', ctrl.signal)).rejects.toMatchObject({ name: 'AbortError' })
  })
})
