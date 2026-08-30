type Props = {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}

export default function SearchBox({ value, onChange, placeholder }: Props) {
  return (
    <div style={{ position: 'relative' }}>
      <span style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)', fontSize: '14px' }}>⌕</span>
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
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
