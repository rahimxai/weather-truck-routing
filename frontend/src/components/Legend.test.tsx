// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import Legend from './Legend'

afterEach(cleanup)

const toggle = () => screen.getByRole('button', { name: 'Guide to the map' })
const key = () => screen.queryByRole('region', { name: 'How to read the map' })

describe('Legend key', () => {
  it('starts closed', () => {
    render(<Legend />)
    expect(toggle()).toHaveProperty('ariaExpanded', 'false')
    expect(key()).toBeNull()
  })

  it('shows the thresholds when opened', async () => {
    render(<Legend />)
    await userEvent.click(toggle())
    expect(toggle()).toHaveProperty('ariaExpanded', 'true')
    const row = screen.getByRole('row', { name: /High/ })
    expect(
      within(row)
        .getAllByRole('cell')
        .map((c) => c.textContent),
    ).toEqual(['35–45', '0.25–0.50', '1.0–2.0'])
    expect(key()?.textContent).toContain('Over 30,000 lb, wind of 45–55 mph is No Travel.')
  })

  it('closes on escape and gives focus back', async () => {
    render(<Legend />)
    await userEvent.click(toggle())
    await userEvent.keyboard('{Escape}')
    expect(key()).toBeNull()
    expect(document.activeElement).toBe(toggle())
  })

  it('closes from its own button', async () => {
    render(<Legend />)
    await userEvent.click(toggle())
    await userEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(key()).toBeNull()
  })
})
