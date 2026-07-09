/** Shared markdown cleanup for Adobe CMS markup, citation markers, and doc links. */

export function sanitizeAdobeMarkup(text: string): string {
  return text
    .replace(/\[!UICONTROL\s+([^\]]+)\]/g, '`$1`')
    .replace(/\[!DNL\s+([^\]]+)\]/g, '**$1**')
    .replace(/>\[!(IMPORTANT|NOTE|TIP|WARNING)\]\s*/g, '> **$1:** ')
}

export function stripCitationMarkers(text: string): string {
  return text.replace(/\[\d+\](?!\()/g, '')
}

export function stripMdLinks(text: string): string {
  return text
    .replace(/\[([^\]]+)\]\([^)]*\.md[^)]*\)/g, '$1')
    // Strip inline EXL/developer.adobe.com doc links — 404-prone; citations panel handles sources
    .replace(/\[([^\]]+)\]\(https?:\/\/(?:experienceleague|developer)\.adobe\.com[^)]+\)/g, '$1')
}
