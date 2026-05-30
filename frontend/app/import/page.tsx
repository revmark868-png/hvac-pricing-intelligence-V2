'use client'

import Link from 'next/link'
import { ArrowLeft, BarChart3, CheckCircle2, FileUp, Layers, TrendingUp, Wand2 } from 'lucide-react'
import { useMemo, useState } from 'react'

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000'

type AnalysisChannel = 'rules' | 'openai' | 'ollama'

type ImportRow = {
  row_number: number
  sku: string | null
  name: string
  category: string
  brand: string | null
  unit: string
  vendor: string
  region: string
  unit_cost: number | null
  source: string | null
  confidence: number
  errors: string[]
}

type ImportResult = {
  filename: string
  imported: boolean
  ai_used: boolean
  ai_provider: string
  total_rows: number
  valid_rows: number
  invalid_rows: number
  created_items: number
  created_quotes: number
  skipped_rows: number
  rows: ImportRow[]
}

const channelLabels: Record<string, string> = {
  rules: 'Rules',
  openai: 'OpenAI',
  ollama: 'Ollama',
}

function money(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '-'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function compactSource(source: string | null | undefined) {
  if (!source) return 'Upload'
  return source.split(' - ').slice(-2).join(' - ')
}

function modelFamily(row: ImportRow) {
  const sku = row.sku ?? row.name
  const match = sku.match(/^[A-Za-z]+/)
  return match?.[0].toUpperCase() ?? row.category.toUpperCase()
}

function countBy<T extends string>(items: T[]) {
  return items.reduce<Record<string, number>>((acc, item) => {
    acc[item] = (acc[item] ?? 0) + 1
    return acc
  }, {})
}

export default function ImportPage() {
  const [file, setFile] = useState<File | null>(null)
  const [vendor, setVendor] = useState('Imported Vendor')
  const [region, setRegion] = useState('DFW')
  const [analysisChannel, setAnalysisChannel] = useState<AnalysisChannel>('rules')
  const [commit, setCommit] = useState(false)
  const [status, setStatus] = useState('Choose a price sheet to preview or import.')
  const [result, setResult] = useState<ImportResult | null>(null)

  async function upload() {
    if (!file) return
    setStatus(commit ? 'Importing valid rows' : 'Parsing preview')
    const form = new FormData()
    form.append('file', file)
    form.append('vendor', vendor)
    form.append('region', region)
    form.append('ai_provider', analysisChannel)
    form.append('commit', String(commit))

    let res: Response
    try {
      res = await fetch(`${apiBase}/imports/prices`, { method: 'POST', body: form })
    } catch (error) {
      throw new Error(`Cannot reach the backend at ${apiBase}. Make sure the FastAPI server is running and this site is allowed by backend CORS settings.`)
    }

    const data = await res.json().catch(() => null)
    if (!data) throw new Error(`Backend returned ${res.status} without a JSON response`)
    if (!res.ok) throw new Error(data.detail || 'Import failed')
    setResult(data)
    setStatus(data.imported ? `Imported ${data.created_quotes} quotes` : `Previewed ${data.total_rows} rows`)
  }

  const analysis = useMemo(() => {
    const rows = result?.rows ?? []
    const validRows = rows.filter((row) => row.unit_cost != null && row.errors.length === 0)
    const prices = validRows.map((row) => row.unit_cost!)
    const avg = prices.reduce((sum, price) => sum + price, 0) / Math.max(prices.length, 1)
    const min = prices.length ? Math.min(...prices) : null
    const max = prices.length ? Math.max(...prices) : null
    const sorted = [...validRows].sort((a, b) => (a.unit_cost ?? 0) - (b.unit_cost ?? 0))
    const familyCounts = Object.entries(countBy(validRows.map(modelFamily)))
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
    const sourceCounts = Object.entries(countBy(validRows.map((row) => compactSource(row.source))))
      .sort((a, b) => b[1] - a[1])
    const categoryCounts = Object.entries(countBy(validRows.map((row) => row.category || 'uncategorized')))
      .sort((a, b) => b[1] - a[1])
    const range = max != null && min != null ? max - min : null
    const conclusion = validRows.length
      ? `${validRows.length} valid prices across ${familyCounts.length} model groups; ${compactSource(sourceCounts[0]?.[0])} contributes the largest share.`
      : 'Upload a file to generate coverage, price range, and model group analysis.'
    return {
      avg,
      min,
      max,
      range,
      validRows,
      lowest: sorted.slice(0, 3),
      highest: sorted.slice(-3).reverse(),
      familyCounts,
      sourceCounts,
      categoryCounts,
      conclusion,
    }
  }, [result])

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>AI Price Import</h1>
          <p>Upload Excel, CSV, TSV, or PDF price sheets and normalize them into quote records.</p>
        </div>
        <Link className="button secondary" href="/">
          <ArrowLeft size={18} /> Dashboard
        </Link>
      </header>

      <section className="import-layout">
        <div className="panel">
          <h2>Upload</h2>
          <label className="dropzone">
            <FileUp size={38} />
            <strong>{file?.name || 'Select vendor price sheet'}</strong>
            <span>.xlsx, .csv, .tsv, .pdf</span>
            <input type="file" accept=".xlsx,.xlsm,.xltx,.xltm,.csv,.tsv,.pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>
          <div className="form-grid">
            <label><span>Default vendor</span><input value={vendor} onChange={(event) => setVendor(event.target.value)} /></label>
            <label><span>Default region</span><input value={region} onChange={(event) => setRegion(event.target.value)} /></label>
            <label>
              <span>Price analysis channel</span>
              <select value={analysisChannel} onChange={(event) => setAnalysisChannel(event.target.value as AnalysisChannel)}>
                <option value="rules">Rules parser</option>
                <option value="ollama">Local Ollama</option>
                <option value="openai">OpenAI</option>
              </select>
            </label>
          </div>
          <label className="toggle">
            <input type="checkbox" checked={commit} onChange={(event) => setCommit(event.target.checked)} />
            <span>Import valid rows into price comparison system</span>
          </label>
          <button className="button primary wide" disabled={!file} onClick={() => upload().catch((error) => setStatus(error.message))}>
            <Wand2 size={18} /> {commit ? 'Parse and Import' : 'Preview Import'}
          </button>
          <p className="status">{status}</p>
        </div>

        <div className="panel">
          <h2>Import Summary</h2>
          <div className="summary-grid">
            <div><span>Rows</span><strong>{result?.total_rows ?? 0}</strong></div>
            <div><span>Valid</span><strong>{result?.valid_rows ?? 0}</strong></div>
            <div><span>Invalid</span><strong>{result?.invalid_rows ?? 0}</strong></div>
            <div><span>Channel</span><strong>{channelLabels[result?.ai_provider ?? analysisChannel] ?? result?.ai_provider ?? 'Rules'}</strong></div>
            <div><span>AI used</span><strong>{result?.ai_used ? 'Yes' : 'No'}</strong></div>
            <div><span>Average</span><strong>{money(analysis.avg)}</strong></div>
            <div><span>Min / Max</span><strong>{money(analysis.min)} / {money(analysis.max)}</strong></div>
            <div><span>Range</span><strong>{money(analysis.range)}</strong></div>
          </div>
          <div className="insight-strip">
            <TrendingUp size={18} />
            <span>{analysis.conclusion}</span>
          </div>
          {result?.imported && (
            <div className="success"><CheckCircle2 size={18} /> Created {result.created_items} items and {result.created_quotes} quotes.</div>
          )}
        </div>
      </section>

      {result && (
        <section className="analysis-grid">
          <div className="panel">
            <div className="panel-head compact-head">
              <div>
                <h2>Model Coverage</h2>
                <p>Count by model prefix</p>
              </div>
              <BarChart3 size={20} />
            </div>
            <div className="bar-list">
              {analysis.familyCounts.map(([label, count]) => (
                <div className="bar-row" key={label}>
                  <span>{label}</span>
                  <div><i style={{ width: `${(count / Math.max(...analysis.familyCounts.map((item) => item[1]), 1)) * 100}%` }} /></div>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-head compact-head">
              <div>
                <h2>Source Coverage</h2>
                <p>Rows captured from each table block</p>
              </div>
              <Layers size={20} />
            </div>
            <div className="bar-list">
              {analysis.sourceCounts.map(([label, count]) => (
                <div className="bar-row source-row" key={label}>
                  <span>{label}</span>
                  <div><i style={{ width: `${(count / Math.max(...analysis.sourceCounts.map((item) => item[1]), 1)) * 100}%` }} /></div>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-head compact-head">
              <div>
                <h2>Price Extremes</h2>
                <p>Lowest and highest captured prices</p>
              </div>
              <TrendingUp size={20} />
            </div>
            <div className="price-extremes">
              <div>
                <span>Lowest</span>
                {analysis.lowest.map((row) => <strong key={`low-${row.sku}-${row.unit_cost}`}>{row.sku || row.name}<em>{money(row.unit_cost)}</em></strong>)}
              </div>
              <div>
                <span>Highest</span>
                {analysis.highest.map((row) => <strong key={`high-${row.sku}-${row.unit_cost}`}>{row.sku || row.name}<em>{money(row.unit_cost)}</em></strong>)}
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="panel table-panel">
        <div className="panel-head">
          <div>
            <h2>Normalized Rows</h2>
            <p>{result ? result.filename : 'No file parsed yet'}</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Row</th><th>SKU</th><th>Name</th><th>Category</th><th>Brand</th><th>Source</th><th>Price</th><th>Confidence</th><th>Errors</th>
              </tr>
            </thead>
            <tbody>
              {(result?.rows ?? []).map((row, index) => (
                <tr key={`${row.source ?? result?.filename ?? 'upload'}-${row.row_number}-${index}`} className={row.errors.length ? 'bad-row' : ''}>
                  <td>{row.row_number}</td>
                  <td>{row.sku || '-'}</td>
                  <td><strong>{row.name || '-'}</strong><span>{row.unit}</span></td>
                  <td>{row.category}</td>
                  <td>{row.brand || '-'}</td>
                  <td>{compactSource(row.source)}</td>
                  <td>{money(row.unit_cost)}</td>
                  <td>{Math.round(row.confidence * 100)}%</td>
                  <td>{row.errors.join(', ') || '-'}</td>
                </tr>
              ))}
              {!result && <tr><td colSpan={9}>Parsed rows will appear here.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}
