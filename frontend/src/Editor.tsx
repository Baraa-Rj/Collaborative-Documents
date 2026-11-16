import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect, useRef, useState } from "react";
import { api, ApiError, type Doc } from "./api";
import Toolbar from "./Toolbar";

type SaveStatus = "idle" | "saving" | "saved" | "error";
type Patch = { title?: string; content_html?: string };

const AUTOSAVE_DELAY_MS = 1000;

export default function Editor({ docId, onSaved }: { docId: number; onSaved: () => void }) {
  const [doc, setDoc] = useState<Doc | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState<SaveStatus>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  // Autosave state lives in refs: it changes on every keystroke and must not trigger re-renders.
  const pending = useRef<Patch>({});
  const timer = useRef<number | undefined>(undefined);
  const queue = useRef<Promise<void>>(Promise.resolve()); // saves run one at a time, in order

  function flush() {
    window.clearTimeout(timer.current);
    const patch = pending.current;
    if (Object.keys(patch).length === 0) return;
    pending.current = {};
    setStatus("saving");
    queue.current = queue.current.then(async () => {
      try {
        await api.updateDoc(docId, patch);
        setSaveError(null);
        // Only show "Saved" if nothing new was typed while this request was in flight.
        setStatus(Object.keys(pending.current).length ? "saving" : "saved");
        onSaved(); // refresh the sidebar (title and "last updated" time)
      } catch (e) {
        setStatus("error");
        setSaveError((e as ApiError).message);
        // Keep the failed changes so the next edit (or retry) re-sends them.
        pending.current = { ...patch, ...pending.current };
      }
    });
  }

  function schedule(patch: Patch) {
    pending.current = { ...pending.current, ...patch };
    setStatus("saving");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(flush, AUTOSAVE_DELAY_MS);
  }

  const editor = useEditor({
    extensions: [StarterKit.configure({ heading: { levels: [1, 2, 3] }, link: { openOnClick: false } })],
    content: "",
    editable: false, // enabled once the document has loaded
    onUpdate: ({ editor }) => schedule({ content_html: editor.getHTML() }),
  });

  useEffect(() => {
    let cancelled = false;
    api
      .getDoc(docId)
      .then((d) => {
        if (cancelled) return;
        setDoc(d);
        setTitle(d.title);
        // emitUpdate false on both calls: just opening a document must not trigger an autosave
        // (Tiptap's setEditable emits an update by default).
        editor?.commands.setContent(d.content_html, { emitUpdate: false });
        editor?.setEditable(true, false);
      })
      .catch((e: ApiError) => {
        if (cancelled) return;
        setLoadError(e.status === 404 ? "Document not found, or you don't have access to it." : e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [docId, editor]);

  // Save anything pending when leaving the document (switching docs or users).
  useEffect(() => () => flush(), []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loadError) return <div className="banner error">{loadError}</div>;
  if (!doc || !editor) return <p className="muted">Loading document…</p>;

  function onTitleChange(value: string) {
    setTitle(value);
    const trimmed = value.trim();
    if (trimmed.length >= 1 && trimmed.length <= 200) schedule({ title: trimmed });
  }

  const titleInvalid = title.trim().length === 0;

  return (
    <div className="editor">
      <div className="editor-head">
        <input
          className={titleInvalid ? "title-input invalid" : "title-input"}
          value={title}
          maxLength={200}
          aria-label="Document title"
          onChange={(e) => onTitleChange(e.target.value)}
          onBlur={() => titleInvalid && setTitle(doc.title)}
        />
        <SaveIndicator status={status} error={saveError} onRetry={flush} />
      </div>
      <p className="doc-info muted">
        Owner: {doc.is_owner ? "you" : doc.owner.name}
        {doc.shared_with.length > 0 && <> · Shared with {doc.shared_with.map((u) => u.name).join(", ")}</>}
      </p>
      {titleInvalid && <p className="field-error">Title can't be empty.</p>}
      <Toolbar editor={editor} />
      <EditorContent editor={editor} className="editor-content" />
    </div>
  );
}

function SaveIndicator({ status, error, onRetry }: { status: SaveStatus; error: string | null; onRetry: () => void }) {
  if (status === "saving") return <span className="save-status">Saving…</span>;
  if (status === "saved") return <span className="save-status ok">Saved</span>;
  if (status === "error")
    return (
      <span className="save-status err" title={error ?? ""}>
        Error saving: {error} <button onClick={onRetry}>Retry</button>
      </span>
    );
  return null;
}
