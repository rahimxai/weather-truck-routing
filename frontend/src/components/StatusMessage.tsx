interface Props {
  tone: 'danger' | 'info' | 'error'
  children: React.ReactNode
}

export default function StatusMessage({ tone, children }: Props) {
  return (
    <p className={`status ${tone}`} role={tone === 'info' ? 'status' : 'alert'}>
      {children}
    </p>
  )
}
