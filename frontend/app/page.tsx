'use client'

import Link from 'next/link'
import { RefreshCcw, Search, Upload } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000'

type Benchmark = {
  item_id: number
  sku: string | null
  name: string
  category: string
  brand: string | null
  quote_count: number
  min_cost: number | null
  avg_cost: number | null
  max_cost: number | null
  best_vendor: string | null
}

function money(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '-'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

export default function Home() {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('Ready')

  async function load() {
    setStatus('Loading')
    const qs = query ? `?q=${encodeURIComponent(query)}` : ''
    const res = await fetch(`${apiBase}/benchmarks${qs}`)
    if (!res.ok) throw new Error('Backend is not responding')
    setBenchmarks(await res.json())
    setStatus('Ready')
  }

  useEffect(() => {
    load().catch((error) => setStatus(error.message))
  }, [])

  const summary = useMemo(() => {
    const quoted = benchmarks.filter((row) => row.quote_count > 0)
    const avg = quoted.reduce((sum, row) => sum + (row.avg_cost ?? 0), 0) / Math.max(quoted.length, 1)
    const savings = quoted.reduce((sum, row) => sum + Math.max((row.max_cost ?? 0) - (row.min_cost ?? 0), 0), 0)
    return { items: benchmarks.length, quoted: quoted.length, avg, savings }
  }, [benchmarks])

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>HVAC Pricing Intelligence AI</h1>
          <p>Import vendor sheets, normalize messy prices, and compare real quote data.</p>
        </div>
        <div className="actions">
          <Link className="button primary" href="/import">
            <Upload size={18} /> Import Prices
          </Link>
          <button className="icon-button" onClick={() => load()} title="Refresh">
            <RefreshCcw size={18} />
          </button>
        </div>
      </header>

      <section className="metrics">
        <div className="metric"><span>Tracked items</span><strong>{summary.items}</strong></div>
        <div className="metric"><span>Quoted items</span><strong>{summary.quoted}</strong></div>
        <div className="metric"><span>Average cost</span><strong>{money(summary.avg)}</strong></div>
        <div className="metric"><span>Potential spread</span><strong>{money(summary.savings)}</strong></div>
      </section>

      <section className="panel table-panel">
        <div className="panel-head">
          <div>
            <h2>Price Benchmarks</h2>
            <p>{status}</p>
          </div>
          <form className="search" onSubmit={(event) => { event.preventDefault(); load().catch((error) => setStatus(error.message)) }}>
            <Search size={17} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search SKU, equipment, material" />
            <button>Search</button>
          </form>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th>Category</th>
                <th>Brand</th>
                <th>Quotes</th>
                <th>Min</th>
                <th>Avg</th>
                <th>Max</th>
                <th>Best Vendor</th>
              </tr>
            </thead>
            <tbody>
              {benchmarks.map((row) => (
                <tr key={row.item_id}>
                  <td><strong>{row.name}</strong><span>{row.sku || 'No SKU'}</span></td>
                  <td>{row.category}</td>
                  <td>{row.brand || '-'}</td>
                  <td>{row.quote_count}</td>
                  <td>{money(row.min_cost)}</td>
                  <td>{money(row.avg_cost)}</td>
                  <td>{money(row.max_cost)}</td>
                  <td>{row.best_vendor || '-'}</td>
                </tr>
              ))}
              {!benchmarks.length && <tr><td colSpan={8}>No price records yet. Import a vendor sheet to begin.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}
