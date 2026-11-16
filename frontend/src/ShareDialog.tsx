import { useState, type FormEvent } from "react";
import { api, ApiError, type Doc } from "./api";

type Props = { doc: Doc; onClose: () => void; onShared: (doc: Doc) => void };

// Owner-only dialog. The backend enforces "only the owner can share"; this UI just hides the option from others.
export default function ShareDialog({ doc, onClose, onShared }: Props) {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const target = email.trim();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      onShared(await api.shareDoc(doc.id, target));
      setMessage(`Shared with ${target}.`);
      setEmail("");
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="overlay" onMouseDown={onClose} onKeyDown={(e) => e.key === "Escape" && onClose()}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-title"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <h2 id="share-title">Share “{doc.title}”</h2>
        <p className="muted">People you share with can view and edit. Only you, the owner, can share.</p>
        <form onSubmit={submit} className="share-form">
          <input
            type="email"
            required
            autoFocus
            placeholder="e.g. bob@ajaia.test"
            aria-label="Email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button className="primary-inline" type="submit" disabled={busy || !email.trim()}>
            {busy ? "Sharing…" : "Share"}
          </button>
        </form>
        {error && <p className="field-error" role="alert">{error}</p>}
        {message && <p className="success">{message}</p>}

        <h3 className="section-title">Who has access</h3>
        <ul className="access-list">
          <li>
            {doc.owner.name} <span className="muted">({doc.owner.email})</span> — Owner
          </li>
          {doc.shared_with.map((u) => (
            <li key={u.id}>
              {u.name} <span className="muted">({u.email})</span> — Can edit
            </li>
          ))}
        </ul>
        <div className="dialog-actions">
          <button onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}
