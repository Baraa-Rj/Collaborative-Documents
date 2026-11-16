import { useEditorState, type Editor } from "@tiptap/react";

// Tiptap v3 doesn't re-render on every keystroke, so useEditorState subscribes to just the active marks we show.
export default function Toolbar({ editor }: { editor: Editor }) {
  const s = useEditorState({
    editor,
    selector: ({ editor }) => ({
      bold: editor.isActive("bold"),
      italic: editor.isActive("italic"),
      underline: editor.isActive("underline"),
      h1: editor.isActive("heading", { level: 1 }),
      h2: editor.isActive("heading", { level: 2 }),
      h3: editor.isActive("heading", { level: 3 }),
      bullet: editor.isActive("bulletList"),
      ordered: editor.isActive("orderedList"),
    }),
  });
  const chain = () => editor.chain().focus();

  const buttons: [string, string, boolean, () => void][] = [
    ["B", "Bold", s.bold, () => chain().toggleBold().run()],
    ["I", "Italic", s.italic, () => chain().toggleItalic().run()],
    ["U", "Underline", s.underline, () => chain().toggleUnderline().run()],
    ["H1", "Heading 1", s.h1, () => chain().toggleHeading({ level: 1 }).run()],
    ["H2", "Heading 2", s.h2, () => chain().toggleHeading({ level: 2 }).run()],
    ["H3", "Heading 3", s.h3, () => chain().toggleHeading({ level: 3 }).run()],
    ["• List", "Bullet list", s.bullet, () => chain().toggleBulletList().run()],
    ["1. List", "Numbered list", s.ordered, () => chain().toggleOrderedList().run()],
  ];

  return (
    <div className="toolbar" role="toolbar" aria-label="Formatting">
      {buttons.map(([label, title, active, run]) => (
        <button
          key={title}
          type="button"
          title={title}
          aria-pressed={active}
          className={active ? "tool active" : "tool"}
          // preventDefault keeps the editor's selection when clicking a toolbar button
          onMouseDown={(e) => e.preventDefault()}
          onClick={run}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
