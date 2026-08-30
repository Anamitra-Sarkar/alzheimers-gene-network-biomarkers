import { useEffect, useState } from 'react'
import GeneTable from './components/GeneTable'
import SearchBox from './components/SearchBox'
import Banner from './components/Banner'

type Health = {
  status: string
  model_loaded: boolean
  model_revision: string | null
  model_approved: boolean
}

type GeneScore = {
  gene: string
  symbol: string
  rwr_score: number
  degree: number
  pagerank: number
  betweenness: number
  closeness: number
  fusion_score: number | null
  rank: number
  seed_contributors: string[]
  is_seed: boolean
}

type RankingResponse = {
  genes: GeneScore[]
  total_genes: number
  model_loaded: boolean
  model_revision: string | null
  query: string | null
}

const API = import.meta.env.VITE_API_URL || ''

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [ranking, setRanking] = useState<RankingResponse | null>(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<GeneScore | null>(null)

  async function fetchHealth() {
    try {
      const r = await fetch(`${API}/health`)
      const j = await r.json()
      setHealth(j)
    } catch {
      setHealth({ status: 'unreachable', model_loaded: false, model_revision: null, model_approved: false })
    }
  }

  async function fetchRanking(q: string) {
    setLoading(true)
    try {
      const url = new URL(`${API}/genes/ranking`, window.location.origin)
      // when API is relative, construct properly
      let fetchUrl = `${API}/genes/ranking?limit=100`
      if (q) fetchUrl += `&q=${encodeURIComponent(q)}`
      const r = await fetch(fetchUrl)
      const j = await r.json()
      setRanking(j)
    } catch {
      setRanking({ genes: [], total_genes: 0, model_loaded: false, model_revision: null, query: q })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHealth()
    fetchRanking('')
  }, [])

  function handleSearch(q: string) {
    setQuery(q)
    fetchRanking(q)
  }

  const modelLoaded = health?.model_loaded ?? ranking?.model_loaded ?? false

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ background: '#fff', borderBottom: '1px solid var(--border)', padding: '16px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 700, letterSpacing: '-0.02em' }}>AD Gene Network</h1>
          <p style={{ fontSize: '13px', color: 'var(--muted)' }}>RWR propagation over STRING PPI + fusion ranking · Alzheimer's biomarker discovery</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', padding: '4px 10px', borderRadius: '999px', background: modelLoaded ? '#ecfdf5' : '#fef2f2', color: modelLoaded ? '#065f46' : '#991b1b', border: `1px solid ${modelLoaded ? '#a7f3d0' : '#fecaca'}` }}>
            {modelLoaded ? `● Model ${health?.model_revision ?? ''} loaded` : '○ Model not released'}
          </span>
          <a href="https://string-db.org/api/" target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: 'var(--muted)' }}>STRING API</a>
        </div>
      </header>

      <Banner modelLoaded={modelLoaded} revision={health?.model_revision} />

      <main style={{ flex: 1, maxWidth: '1100px', width: '100%', margin: '0 auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <section style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px' }}>
          <h2 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>Search genes</h2>
          <SearchBox value={query} onChange={handleSearch} placeholder="Filter by symbol, e.g. APOE, TREM2, BIN1..." />
          <p style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '8px' }}>
            Scores are RWR steady-state probabilities fused with degree/PageRank/betweenness/closeness. Seed genes (26 known AD loci) anchor the walk with restart 0.3.
          </p>
        </section>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>Loading ranking…</div>
        ) : (
          <GeneTable genes={ranking?.genes ?? []} total={ranking?.total_genes ?? 0} modelLoaded={modelLoaded} onSelect={setSelected} />
        )}

        {selected && (
          <section style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 600 }}>{selected.gene} <span style={{ color: 'var(--muted)', fontWeight: 400 }}>rank #{selected.rank}</span></h3>
              <button onClick={() => setSelected(null)} style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '6px', padding: '4px 10px', cursor: 'pointer' }}>Close</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginTop: '16px' }}>
              <div><div style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Fusion score</div><div style={{ fontWeight: 600 }} className="mono">{selected.fusion_score?.toFixed(4) ?? '—'}</div></div>
              <div><div style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase' }}>RWR score</div><div className="mono">{selected.rwr_score.toExponential(3)}</div></div>
              <div><div style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase' }}>PageRank</div><div className="mono">{selected.pagerank.toFixed(4)}</div></div>
              <div><div style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase' }}>Degree</div><div className="mono">{selected.degree.toFixed(1)}</div></div>
            </div>
            <div style={{ marginTop: '12px', fontSize: '13px' }}>
              <span style={{ color: 'var(--muted)' }}>Seed contributors: </span>
              {selected.seed_contributors.length ? selected.seed_contributors.join(', ') : <em style={{ color: 'var(--muted)' }}>{selected.is_seed ? 'This is a seed gene' : 'No single dominant seed; diffuse network proximity'}</em>}
              {selected.is_seed && <span style={{ marginLeft: '8px', background: 'var(--accent-light)', color: 'var(--accent)', padding: '2px 6px', borderRadius: '4px', fontSize: '11px' }}>SEED</span>}
            </div>
          </section>
        )}
      </main>

      <footer style={{ textAlign: 'center', padding: '16px', fontSize: '12px', color: 'var(--muted)', borderTop: '1px solid var(--border)', background: '#fff' }}>
        Real data: STRING PPI 9606.protein.links.v12.0 · Seed genes from Lambert/Kunkle/Bellenguez GWAS · RWR r=0.3 · Fusion: logistic/GBT
      </footer>
    </div>
  )
}
