type Props = {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  id?: string
}

export default function SearchBox({ value, onChange, placeholder, id = "gene-search" }: Props) {
  return (
    <div style={{ position: 'relative' }}>
      <label htmlFor={id} style={{ position: 'absolute', width: '1px', height: '1px', overflow: 'hidden', clip: 'rect(0,0,0,0)' }}>
        Search genes by symbol
      </label>
      <span aria-hidden="true" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)', fontSize: '14px' }}>⌕</span>
      <input
        id={id}
        type="search"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label="Search genes by symbol"
        autoComplete="off"
        style={{
          width: '100%',
          padding: '10px 12px 10px 30px',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          fontSize: '14px',
          outline: 'none',
        }}
        onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
        onBlur={e => (e.target.style.borderColor = 'var(--border)')}
      />
    </div>
  )
}
