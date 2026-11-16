import { useCallback, useEffect, useState } from "react";
import { api, ApiError, MAX_IMPORT_BYTES, setCurrentUser, type DocList, type User } from "./api";
import DocListPanel from "./DocListPanel";
import Editor from "./Editor";

// The open document lives in the URL hash (#/doc/5) so a refresh reopens it.
function docIdFromHash(): number | null {
  const m = window.location.hash.match(/^#\/doc\/(\d+)$/);
  return m ? Number(m[1]) : null;
}

const USER_KEY = "ajaia.userId";

export default function App() {
  const [users, setUsers] = useState<User[]>([]);
  const [userId, setUserId] = useState<number | null>(null);
  const [docs, setDocs] = useState<DocList | null>(null);
  const [docId, setDocId] = useState<number | null>(docIdFromHash);
  const [error, setError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  // Load the seeded users once, and restore the last selected user.
  useEffect(() => {
    api
      .users()
      .then((list) => {
        setUsers(list);
        const saved = Number(localStorage.getItem(USER_KEY));
        const initial = list.find((u) => u.id === saved) ?? list[0];
        setCurrentUser(initial.id);
        setUserId(initial.id);
      })
      .catch((e: ApiError) => setError(e.message));
  }, []);

  useEffect(() => {
    const onHash = () => setDocId(docIdFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const refreshDocs = useCallback(() => {
    api.listDocs().then(setDocs).catch((e: ApiError) => setError(e.message));
  }, []);

  useEffect(() => {
    if (userId !== null) refreshDocs();
  }, [userId, refreshDocs]);

  function openDoc(id: number | null) {
    window.location.hash = id === null ? "" : `/doc/${id}`;
  }

  function switchUser(id: number) {
    setCurrentUser(id);
    localStorage.setItem(USER_KEY, String(id));
    setDocs(null);
    setUserId(id);
    openDoc(null); // the open doc may not be visible to the new user
  }

  async function createDoc() {
    try {
      const doc = await api.createDoc();
      refreshDocs();
      openDoc(doc.id);
    } catch (e) {
      setError((e as ApiError).message);
    }
  }

  async function importDoc(file: File) {
    setError(null);
    if (file.size > MAX_IMPORT_BYTES) {
      setError(`"${file.name}" is larger than the 2 MB import limit.`);
      return;
    }
    setImporting(true);
    try {
      const doc = await api.importDoc(file);
      refreshDocs();
      openDoc(doc.id);
    } catch (e) {
      setError(`Import failed: ${(e as ApiError).message}`);
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <strong className="brand">Ajaia Docs</strong>
        <div className="user-switcher">
          <span className="mock-badge" title="Mock auth: requests just send X-User-Id. Not secure.">
            Demo login — not secure
          </span>
          <label>
            Signed in as{" "}
            <select value={userId ?? ""} onChange={(e) => switchUser(Number(e.target.value))}>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name} ({u.email})
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {error && (
        <div className="banner error" role="alert">
          {error} <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      <div className="layout">
        <DocListPanel
          docs={docs}
          activeId={docId}
          importing={importing}
          onOpen={openDoc}
          onCreate={createDoc}
          onImport={importDoc}
        />
        <main className="main">
          {userId !== null && docId !== null ? (
            // key: remount the editor per (user, doc) so no state leaks between documents or users.
            <Editor key={`${userId}-${docId}`} docId={docId} onSaved={refreshDocs} />
          ) : (
            <div className="empty">Select a document or create a new one.</div>
          )}
        </main>
      </div>
    </div>
  );
}
