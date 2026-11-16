"""Server-side HTML sanitization. Documents are shared between users, so unsanitized HTML
would be a stored-XSS hole. Every write path (create, update, import) goes through clean_html()."""
import nh3

# Only what the Tiptap editor (StarterKit) can produce. Anything else is stripped;
# its text content is kept, except <script>/<style> which nh3 drops entirely.
ALLOWED_TAGS = {
    "p", "br", "hr",
    "h1", "h2", "h3",
    "strong", "em", "u", "s", "code", "pre", "blockquote",
    "ul", "ol", "li",
    "a",
}
ALLOWED_ATTRIBUTES = {
    "a": {"href"},     # nh3 only keeps safe URL schemes (http, https, mailto, ...) and adds rel="noopener noreferrer"
    "ol": {"start"},
}


def clean_html(html: str) -> str:
    return nh3.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
