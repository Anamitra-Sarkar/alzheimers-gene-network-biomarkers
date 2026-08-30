type Gene = {
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

export default function GeneTable({ genes, total, modelLoaded, onSelect }: { genes: Gene[]; total: number; modelLoaded: boolean; onSelect: (g: Gene) => void }) {
  if (!modelLoaded) {
    return (
      <div style={{ background: '#fff', border: '1px dashed var(--border)', borderRadius: '12px', padding: '32px', textAlign: 'center', color: 'var(--muted)' }}>
        <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)' }}>No ranking available</div>
        <div style={{ fontSize: '13px', marginTop: '4px' }}>The approved model artifact has not been released. The table will populate once the server is deployed with <span className="mono">MODEL_RELEASE_APPROVED=true</span>.</div>
      </div>
    )
  }

  if (genes.length === 0) {
    return (
      <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: '12px', padding: '24px', textAlign: 'center', color: 'var(--muted)' }}>
        No genes match the current filter.
      </div>
    )
  }

  return (
    <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: '12px', overflow: 'hidden' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '13px', fontWeight: 600 }}>Ranked genes <span style={{ color: 'var(--muted)', fontWeight: 400 }}>({total} total)</span></span>
        <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Click a row for explanation · sorted by fusion score</span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ background: '#f9fafb', textAlign: 'left', fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <th style={{ padding: '8px 12px' }}>Rank</th>
              <th style={{ padding: '8px 12px' }}>Gene</th>
              <th style={{ padding: '8px 12px' }}>Fusion</th>
              <th style={{ padding: '8px 12px' }}>RWR</th>
              <th style={{ padding: '8px 12px' }}>PageRank</th>
              <th style={{ padding: '8px 12px' }}>Degree</th>
              <th style={{ padding: '8px 12px' }}>Explain</th>
            </tr>
          </thead>
          <tbody>
            {genes.map(g => (
              <tr
                key={g.gene}
                onClick={() => onSelect(g)}
                style={{ borderTop: '1px solid var(--border)', cursor: 'pointer', background: g.is_seed ? 'var(--accent-light)' : undefined }}
                onMouseEnter={e => (e.currentTarget.style.background = g.is_seed ? '#e0e7ff' : '#f9fafb')}
                onMouseLeave={e => (e.currentTarget.style.background = g.is_seed ? 'var(--accent-light)' : 'transparent')}
              >
                <td style={{ padding: '9px 12px' }} className="mono">{g.rank}</td>
                <td style={{ padding: '9px 12px', fontWeight: 600 }}>
                  {g.gene}
                  {g.is_seed && <span style={{ marginLeft: '6px', fontSize: '10px', background: 'var(--accent)', color: '#fff', padding: '1px 5px', borderRadius: '4px' }}>SEED</span>}
                </td>
                <td style={{ padding: '9px 12px' }} className="mono">{g.fusion_score !== null ? g.fusion_score.toFixed(3) : '—'}</td>
                <td style={{ padding: '9px 12px' }} className="mono">{g.rwr_score.toExponential(2)}</td>
                <td style={{ padding: '9px 12px' }} className="mono">{g.pagerank.toFixed(3)}</td>
                <td style={{ padding: '9px 12px' }} className="mono">{g.degree.toFixed(1)}</td>
                <td style={{ padding: '9px 12px', color: 'var(--muted)', fontSize: '12px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {g.seed_contributors.length ? g.seed_contributors.slice(0, 2).join(', ') : g.is_seed ? '— seed —' : 'diffuse'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
