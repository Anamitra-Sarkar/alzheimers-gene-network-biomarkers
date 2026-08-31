export default function Banner({ modelLoaded, revision }: { modelLoaded: boolean; revision?: string | null }) {
  if (modelLoaded) {
    return (
      <div role="status" aria-live="polite" style={{ background: '#ecfdf5', borderBottom: '1px solid #a7f3d0', padding: '10px 32px', fontSize: '13px', color: '#065f46', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
        <span aria-hidden="true">✓</span><span>Model loaded</span>
        {revision && <span className="mono" style={{ background: '#fff', padding: '1px 6px', borderRadius: '4px', border: '1px solid #a7f3d0', fontSize: '12px' }} aria-label={`revision ${revision}`}>rev {revision}</span>}
        <span style={{ color: '#047857' }}>— ranking reflects RWR+fusion scores over STRING network.</span>
      </div>
    )
  }
  return (
    <div role="alert" aria-live="assertive" style={{ background: 'var(--warn-bg)', borderBottom: '1px solid var(--warn-border)', padding: '12px 32px', fontSize: '13px', color: '#92400e', display: 'flex', gap: '10px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
      <span style={{ fontWeight: 600 }}>Model not yet released</span>
      <span>— the ranking pipeline exists but no approved artifact is loaded. The API is abstaining: /genes/ranking returns empty and /genes/&#123;id&#125; returns 503. Set <span className="mono">MODEL_RELEASE_APPROVED=true</span> and <span className="mono">APPROVED_ARTIFACT_REVISION</span> on the server to enable serving.</span>
    </div>
  )
}
