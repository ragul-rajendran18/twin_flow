export default function ErrorBanner({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  if (!message) return null
  return (
    <div className="error-banner" role="alert">
      <span>{message}</span>
      {onDismiss && (
        <button type="button" className="error-dismiss" onClick={onDismiss}>
          ×
        </button>
      )}
    </div>
  )
}
