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
      <a href="#main-content" style={{ position: 'absolute', left: '-9999px', top: 'auto', width: '1px', height: '1px', overflow: 'hidden' }} onFocus={e => Object.assign(e.currentTarget.style, { left: '16px', top: '16px', width: 'auto', height: 'auto', background: '#fff', padding: '8px 12px', border: '2px solid var(--accent)', borderRadius: '6px', zIndex: 1000 }) as unknown as string} onBlur={e => Object.assign(e.currentTarget.style, { left: '-9999px', width: '1px', height: '1px' }) as unknown as string}>Skip to content</a>
      <nav style={{ maxWidth: '1100px', margin: '0 auto', width: '100%', boxSizing: 'border-box', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 24px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '34px', height: '34px', borderRadius: '9px', background: 'linear-gradient(135deg, #22d3ee, #0f172a)', color: 'white', fontWeight: 700, fontSize: '13px' }}>AD</span>
          <span style={{ fontFamily: "'Fraunces', serif", fontWeight: 600, fontSize: '18px' }}>Gene Network</span>
        </div>
        <span aria-live="polite" style={{ fontSize: '12px', padding: '5px 12px', borderRadius: '999px', background: modelLoaded ? '#ecfdf5' : '#f1f5f9', color: modelLoaded ? '#065f46' : '#475569', border: `1px solid ${modelLoaded ? '#a7f3d0' : '#e2e8f0'}` }}>
          {modelLoaded ? 'Live rankings' : 'Preview mode'}
        </span>
      </nav>

      <section className="ad-hero" style={{ maxWidth: '1100px', margin: '0 auto', width: '100%', boxSizing: 'border-box', display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: '40px', alignItems: 'center', padding: '32px 24px 40px' }}>
        <div>
          <div style={{ textTransform: 'uppercase', letterSpacing: '0.14em', fontSize: '12px', fontWeight: 700, color: '#0e7490', marginBottom: '14px' }}>Alzheimer's biomarker discovery</div>
          <h1 style={{ fontFamily: "'Fraunces', serif", fontWeight: 600, fontSize: '36px', lineHeight: 1.15, margin: '0 0 18px' }}>
            Find the genes that matter, <em style={{ fontStyle: 'italic', color: '#0e7490' }}>ranked and explained.</em>
          </h1>
          <p style={{ color: '#475569', fontSize: '16px', lineHeight: 1.6, maxWidth: '480px', margin: '0 0 26px' }}>
            Gene Network ranks candidate Alzheimer's biomarkers by how connected they are to known disease genes
            within the broader protein interaction network — with every ranking traceable back to its evidence.
          </p>
        </div>
        <figure style={{ margin: 0 }}>
          <img
            src="/hero.png"
            alt="Illustration of a dark navy human brain overlaid with a glowing teal network of interconnected nodes representing gene interactions in Alzheimer's disease research"
            style={{ width: '100%', aspectRatio: '1 / 1', objectFit: 'cover', borderRadius: '18px', border: '1px solid var(--border)', boxShadow: '0 24px 50px rgba(15,23,42,0.15)', display: 'block' }}
            loading="eager"
          />
        </figure>
      </section>

      <section className="ad-features" style={{ maxWidth: '1100px', margin: '0 auto 48px', width: '100%', boxSizing: 'border-box', padding: '0 24px', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '18px' }}>
        <div style={{ background: 'rgba(255,255,255,0.85)', border: '1px solid var(--border)', borderRadius: '14px', padding: '22px' }}>
          <span style={{ display: 'block', fontFamily: "'Fraunces', serif", fontSize: '13px', color: '#0e7490', marginBottom: '8px' }}>01</span>
          <h3 style={{ fontFamily: "'Fraunces', serif", fontWeight: 600, fontSize: '16px', margin: '0 0 8px' }}>Network-grounded scores</h3>
          <p style={{ color: '#64748b', fontSize: '13px', lineHeight: 1.55, margin: 0 }}>Rankings combine multiple measures of network connectivity, not a single metric.</p>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.85)', border: '1px solid var(--border)', borderRadius: '14px', padding: '22px' }}>
          <span style={{ display: 'block', fontFamily: "'Fraunces', serif", fontSize: '13px', color: '#0e7490', marginBottom: '8px' }}>02</span>
          <h3 style={{ fontFamily: "'Fraunces', serif", fontWeight: 600, fontSize: '16px', margin: '0 0 8px' }}>Anchored in known biology</h3>
          <p style={{ color: '#64748b', fontSize: '13px', lineHeight: 1.55, margin: 0 }}>Established Alzheimer's genes anchor the search, so results stay grounded in real evidence.</p>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.85)', border: '1px solid var(--border)', borderRadius: '14px', padding: '22px' }}>
          <span style={{ display: 'block', fontFamily: "'Fraunces', serif", fontSize: '13px', color: '#0e7490', marginBottom: '8px' }}>03</span>
          <h3 style={{ fontFamily: "'Fraunces', serif", fontWeight: 600, fontSize: '16px', margin: '0 0 8px' }}>Every result is traceable</h3>
          <p style={{ color: '#64748b', fontSize: '13px', lineHeight: 1.55, margin: 0 }}>See exactly which known genes contributed to a candidate's ranking.</p>
        </div>
      </section>

      <Banner modelLoaded={modelLoaded} revision={health?.model_revision} />

      <main id="main-content" style={{ flex: 1, maxWidth: '1100px', width: '100%', margin: '0 auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <section aria-labelledby="search-heading" style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px' }}>
          <h2 id="search-heading" style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>Search genes</h2>
          <SearchBox value={query} onChange={handleSearch} placeholder="Filter by symbol, e.g. APOE, TREM2, BIN1..." />
          <p style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '8px' }}>
            Scores are RWR steady-state probabilities fused with degree/PageRank/betweenness/closeness. Seed genes (26 known AD loci) anchor the walk with restart 0.3.
          </p>
        </section>

        {loading ? (
          <div role="status" aria-live="polite" aria-busy="true" style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>Loading ranking…</div>
        ) : (
          <GeneTable genes={ranking?.genes ?? []} total={ranking?.total_genes ?? 0} modelLoaded={modelLoaded} onSelect={setSelected} />
        )}

        {selected && (
          <section aria-labelledby="detail-heading" style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <h3 id="detail-heading" style={{ fontSize: '16px', fontWeight: 600 }}>{selected.gene} <span style={{ color: 'var(--muted)', fontWeight: 400 }}>rank #{selected.rank}</span></h3>
              <button onClick={() => setSelected(null)} aria-label={`Close details for ${selected.gene}`} style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '6px', padding: '4px 10px', cursor: 'pointer' }}>Close</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '12px', marginTop: '16px' }}>
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
        Built on real protein-interaction data and published genome-wide association studies of Alzheimer's disease.
      </footer>
    </div>
  )
}
