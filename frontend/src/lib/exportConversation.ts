import { renderToStaticMarkup } from 'react-dom/server'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sanitizeAdobeMarkup, stripCitationMarkers, stripMdLinks } from './markdownSanitize'
import type { ChatSession } from '@/store/chatStore'

/** Same cleanup ChatMessage applies before rendering — keeps exports consistent with on-screen text. */
function cleanContent(content: string): string {
  return stripMdLinks(stripCitationMarkers(sanitizeAdobeMarkup(content || '')))
}

/** Strip common markdown syntax down to readable plain text. */
function markdownToPlainText(md: string): string {
  return md
    .replace(/```[\s\S]*?```/g, (block) => block.replace(/```[a-z]*\n?|```/g, '').trim())
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // List-bullet markers normalized before bold/italic stripping — otherwise a leading "*" bullet
    // pairs up with the next "*" on the same line (e.g. "* Use *Segments*"), corrupting both.
    .replace(/^\s*[-*+]\s+/gm, '- ')
    .replace(/(\*\*|__)(.*?)\1/g, '$2')
    .replace(/(\*|_)(.*?)\1/g, '$2')
    .replace(/^\s*>\s?/gm, '')
    .replace(/`([^`]+)`/g, '$1')
    .trim()
}

function appOrigin(): string {
  return typeof window !== 'undefined' ? window.location.origin : 'https://rovr.app'
}

/** Absolute URL for a public asset — exports are standalone files, so relative paths won't resolve. */
function assetUrl(filename: string): string {
  const base = import.meta.env.BASE_URL ?? '/'
  return `${appOrigin()}${base}${filename}`
}

const LOGO_URL = () => assetUrl('rovrlogo.png')
const FAVICON_URL = () => assetUrl('favicon.svg')

/**
 * Deep-links back to the specific conversation (via ?conversation=<id>, handled by
 * ChatPage/chatStore.openConversationById) once the turn has been persisted server-side.
 * Falls back to the app root if the conversation hasn't been saved yet (e.g. still streaming).
 */
function conversationUrl(session: ChatSession): string {
  const appRoot = `${appOrigin()}${import.meta.env.BASE_URL ?? '/'}`
  return session.conversationId !== undefined ? `${appRoot}?conversation=${session.conversationId}` : appRoot
}

function sessionTitleLine(session: ChatSession): string {
  const date = new Date(session.createdAt).toLocaleString()
  return `${session.title}\n${date}`
}

export function serializeSessionAsMarkdown(session: ChatSession): string {
  const url = conversationUrl(session)
  const lines = [
    `![Rovr](${LOGO_URL()})`,
    '',
    `# ${sessionTitleLine(session)}`,
    '',
  ]
  for (const msg of session.messages) {
    if (!msg.content.trim()) continue
    const speaker = msg.role === 'user' ? 'You' : 'Rovr'
    lines.push(`### ${speaker}`, '', cleanContent(msg.content), '')
  }
  lines.push(
    '---',
    '',
    `Ask Rovr: [${url}](${url})`,
    '',
    `© Answer by [Rovr](${url}) — AI-generated, verify before acting.`,
  )
  return lines.join('\n').trim() + '\n'
}

export function serializeSessionAsPlainText(session: ChatSession): string {
  const url = conversationUrl(session)
  const lines = ['ROVR', '', sessionTitleLine(session), '']
  for (const msg of session.messages) {
    if (!msg.content.trim()) continue
    const speaker = msg.role === 'user' ? 'You' : 'Rovr'
    lines.push(`${speaker}:`, markdownToPlainText(cleanContent(msg.content)), '')
  }
  lines.push(
    '---',
    `Ask Rovr: ${url}`,
    `© Answer by Rovr (${url}) — AI-generated, verify before acting.`,
  )
  return lines.join('\n').trim() + '\n'
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

const HTML_STYLE = `
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 720px; margin: 40px auto; padding: 0 20px; color: #1e293b; line-height: 1.6; }
  .brand { display: flex; align-items: center; gap: 8px; margin-bottom: 20px; }
  .brand img { height: 28px; width: auto; }
  .brand span { font-weight: 700; font-size: 1.1rem; color: #14532d; }
  h1 { font-size: 1.25rem; margin-bottom: 0; }
  .meta { color: #64748b; font-size: 0.8rem; margin-bottom: 24px; }
  .turn { margin-bottom: 24px; }
  .speaker { font-weight: 600; font-size: 0.85rem; margin-bottom: 6px; }
  .speaker.user { color: #14532d; }
  .speaker.assistant { color: #047857; }
  .bubble { border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 16px; }
  .bubble img { max-width: 100%; border-radius: 8px; }
  .bubble pre { background: #f1f5f9; padding: 10px; border-radius: 8px; overflow-x: auto; }
  .bubble code { background: #f1f5f9; padding: 2px 4px; border-radius: 4px; font-size: 0.85em; }
  .bubble pre code { background: none; padding: 0; }
  .footer { margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 0.75rem; color: #64748b; }
  .footer a { color: #047857; }
  .footer .brand { margin-bottom: 8px; }
  .footer .brand img { height: 18px; }
  .footer .brand span { font-size: 0.85rem; }
`.trim()

/** Hide images that fail to load (e.g. hotlink/referrer-blocked when opened as a local file) — same graceful degradation as DocImage's onError in the live app, inlined since a static export has no React lifecycle. */
function hideBrokenImages(html: string): string {
  return html.replace(/<img /g, '<img onerror="this.style.display=\'none\'" ')
}

export function serializeSessionAsHtml(session: ChatSession): string {
  const url = conversationUrl(session)
  const turns = session.messages
    .filter((msg) => msg.content.trim())
    .map((msg) => {
      const speaker = msg.role === 'user' ? 'You' : 'Rovr'
      const bodyHtml =
        msg.role === 'user'
          ? `<p>${escapeHtml(msg.content)}</p>`
          : hideBrokenImages(
              renderToStaticMarkup(ReactMarkdown({ remarkPlugins: [remarkGfm], children: cleanContent(msg.content) })),
            )
      return `<div class="turn"><div class="speaker ${msg.role}">${speaker}</div><div class="bubble">${bodyHtml}</div></div>`
    })
    .join('\n')

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>${escapeHtml(session.title)} — Rovr</title>
<link rel="icon" type="image/svg+xml" href="${FAVICON_URL()}">
<meta name="description" content="Conversation exported from Rovr, an Adobe Experience League assistant.">
<style>${HTML_STYLE}</style>
</head>
<body>
<div class="brand"><img src="${LOGO_URL()}" alt="Rovr" onerror="this.style.display='none'"><span>Rovr</span></div>
<h1>${escapeHtml(session.title)}</h1>
<div class="meta">${escapeHtml(new Date(session.createdAt).toLocaleString())}</div>
${turns}
<div class="footer">
  <div class="brand"><img src="${LOGO_URL()}" alt="Rovr" onerror="this.style.display='none'"><span>Rovr</span></div>
  <p>Ask Rovr: <a href="${url}">${url}</a></p>
  <p>&copy; Answer by <a href="${url}">Rovr</a> — AI-generated, verify before acting.</p>
</div>
</body>
</html>
`
}

function slugifyTitle(title: string): string {
  return (
    title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 50) || 'conversation'
  )
}

function triggerDownload(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function downloadSessionAsMarkdown(session: ChatSession): void {
  const md = serializeSessionAsMarkdown(session)
  triggerDownload(md, `${slugifyTitle(session.title)}.md`, 'text/markdown')
}

export function downloadSessionAsText(session: ChatSession): void {
  const text = serializeSessionAsPlainText(session)
  triggerDownload(text, `${slugifyTitle(session.title)}.txt`, 'text/plain')
}

export function downloadSessionAsHtml(session: ChatSession): void {
  const html = serializeSessionAsHtml(session)
  triggerDownload(html, `${slugifyTitle(session.title)}.html`, 'text/html')
}
