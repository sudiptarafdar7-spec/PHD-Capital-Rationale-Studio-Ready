"""
ReportLab HTML Conversion Utilities
Converts rich HTML content from database to ReportLab-compatible format
"""

import re


def extract_html_content(html_text):
    """Convert HTML to ReportLab-compatible format, preserving formatting
    
    This function transforms rich HTML content (like disclaimers/disclosures)
    into a subset of HTML tags that ReportLab's Paragraph can safely render.
    
    Supported conversions:
    - Headings (h1-h6) → font sizes + bold
    - Strong/em → b/i
    - Paragraphs/divs → line breaks
    - Lists (ul/ol/li) → bullet points
    - Removes unsupported tags (table, iframe, script, style, para, etc.)
    
    Args:
        html_text: Raw HTML string from database
        
    Returns:
        ReportLab-compatible HTML string
    """
    if not html_text:
        return ""
    
    # If it's already plain text, return as-is
    if '<' not in html_text:
        return html_text.strip()
    
    text = html_text
    
    # Remove document structure tags
    text = re.sub(r'<!DOCTYPE[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</?html[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<head>.*?</head>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'</?body[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<style>.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<script>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Convert HTML5/semantic tags to ReportLab-compatible format
    # Convert headings to bold + larger font + line breaks
    text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'<br/><font size="16"><b>\1</b></font><br/>', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'<br/><font size="14"><b>\1</b></font><br/>', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'<br/><font size="12"><b>\1</b></font><br/>', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'<br/><b>\1</b><br/>', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h5[^>]*>(.*?)</h5>', r'<br/><b>\1</b><br/>', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h6[^>]*>(.*?)</h6>', r'<br/><b>\1</b><br/>', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Convert <strong> and <em> to <b> and <i>
    text = re.sub(r'<strong[^>]*>', '<b>', text, flags=re.IGNORECASE)
    text = re.sub(r'</strong>', '</b>', text, flags=re.IGNORECASE)
    text = re.sub(r'<em[^>]*>', '<i>', text, flags=re.IGNORECASE)
    text = re.sub(r'</em>', '</i>', text, flags=re.IGNORECASE)
    
    # Convert <p> to line breaks
    text = re.sub(r'<p[^>]*>', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '<br/>', text, flags=re.IGNORECASE)
    
    # Convert <div> to line breaks
    text = re.sub(r'<div[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '<br/>', text, flags=re.IGNORECASE)
    
    # Convert lists to bullet points
    text = re.sub(r'<ul[^>]*>', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'</ul>', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'<ol[^>]*>', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'</ol>', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'<li[^>]*>', '• ', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '<br/>', text, flags=re.IGNORECASE)
    
    # Remove unsupported container tags but keep content (including <para>)
    # Note: Table content will be lost - tables are not supported by ReportLab Paragraph
    text = re.sub(r'<(section|article|main|header|footer|nav|aside|container|card|para)[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</(section|article|main|header|footer|nav|aside|container|card|para)>', '', text, flags=re.IGNORECASE)
    
    # Remove tables and their content (not supported)
    text = re.sub(r'<table[^>]*>.*?</table>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Fix br tags - ensure they're self-closing with no space before slash
    text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)
    
    # Clean up multiple consecutive line breaks
    text = re.sub(r'(<br/>){3,}', '<br/><br/>', text, flags=re.IGNORECASE)
    
    # Remove leading/trailing breaks
    text = re.sub(r'^(<br/>)+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(<br/>)+$', '', text, flags=re.IGNORECASE)
    
    # Remove extra whitespace around tags
    text = re.sub(r'>\s+<', '><', text)
    
    return text.strip()
