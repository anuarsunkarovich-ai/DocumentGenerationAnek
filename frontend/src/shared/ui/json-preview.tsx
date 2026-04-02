type JsonPreviewProps = {
  title: string
  payload: unknown
}

export function JsonPreview({ title, payload }: JsonPreviewProps) {
  return (
    <div className="json-preview">
      <p className="micro-label">{title}</p>
      <pre>{JSON.stringify(payload, null, 2)}</pre>
    </div>
  )
}
