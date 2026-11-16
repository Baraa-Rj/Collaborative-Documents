import { useRef } from "react";
import { IMPORT_ACCEPT, type DocList, type DocSummary } from "./api";

type Props = {
  docs: DocList | null;
  activeId: number | null;
  importing: boolean;
  onOpen: (id: number) => void;
  onCreate: () => void;
  onImport: (file: File) => void;
};

export default function DocListPanel({ docs, activeId, importing, onOpen, onCreate, onImport }: Props) {
  const fileInput = useRef<HTMLInputElement>(null);

  return (
    <aside className="sidebar">
      <button className="primary" onClick={onCreate}>
        + New document
      </button>
      <button className="secondary" onClick={() => fileInput.current?.click()} disabled={importing}>
        {importing ? "Importing…" : "Import file"}
      </button>
      <input
        ref={fileInput}
        type="file"
        accept={IMPORT_ACCEPT}
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = ""; // allow picking the same file again after an error
          if (file) onImport(file);
        }}
      />
      <p className="hint">Supported: .txt, .md, .docx (max 2 MB). Imports become a new document you own.</p>
      {docs === null ? (
        <p className="muted">Loading…</p>
      ) : (
        <>
          <Section title="My documents" items={docs.owned} activeId={activeId} onOpen={onOpen} />
          <Section title="Shared with me" items={docs.shared} activeId={activeId} onOpen={onOpen} showOwner />
        </>
      )}
    </aside>
  );
}

function Section(props: {
  title: string;
  items: DocSummary[];
  activeId: number | null;
  onOpen: (id: number) => void;
  showOwner?: boolean;
}) {
  return (
    <section>
      <h2 className="section-title">{props.title}</h2>
      {props.items.length === 0 ? (
        <p className="muted">None yet.</p>
      ) : (
        <ul className="doc-list">
          {props.items.map((d) => (
            <li key={d.id}>
              <button className={d.id === props.activeId ? "doc-item active" : "doc-item"} onClick={() => props.onOpen(d.id)}>
                <span className="doc-title">{d.title}</span>
                <span className="doc-meta">
                  {props.showOwner && <span className="owner-badge">{d.owner.name}</span>}
                  {new Date(d.updated_at).toLocaleString()}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
