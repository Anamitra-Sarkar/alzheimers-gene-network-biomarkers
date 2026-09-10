export default function Banner({ modelLoaded, revision }: { modelLoaded: boolean; revision?: string | null }) {
  if (modelLoaded) {
    return (
      <div role="status" aria-live="polite" style={{ background: '#ecfdf5', borderBottom: '1px solid #a7f3d0', padding: '10px 32px', fontSize: '13px', color: '#065f46', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
        <span aria-hidden="true">✓</span><span>Rankings are live</span>
        {revision && <span className="mono" style={{ background: '#fff', padding: '1px 6px', borderRadius: '4px', border: '1px solid #a7f3d0', fontSize: '12px' }} aria-label={`version ${revision}`}>v{revision}</span>}
      </div>
    )
  }
  return (
    <div role="alert" aria-live="assertive" style={{ background: 'var(--warn-bg)', borderBottom: '1px solid var(--warn-border)', padding: '12px 32px', fontSize: '13px', color: '#92400e', display: 'flex', gap: '10px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
      <span style={{ fontWeight: 600 }}>Rankings aren't available yet</span>
      <span>— our team is finishing validation before enabling live results. Please check back soon.</span>
    </div>
  )
}
