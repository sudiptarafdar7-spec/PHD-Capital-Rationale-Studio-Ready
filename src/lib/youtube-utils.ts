/**
 * Extract YouTube video ID from various URL formats
 * Supports: watch, live, shorts, embed, v, and youtu.be links
 */
export function extractVideoId(url: string): string {
  const patterns = [
    /(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})/,           // youtube.com/watch?v=ID
    /(?:youtu\.be\/)([a-zA-Z0-9_-]{11})/,                       // youtu.be/ID
    /(?:youtube\.com\/live\/)([a-zA-Z0-9_-]{11})/,              // youtube.com/live/ID
    /(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,             // youtube.com/embed/ID
    /(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})/,                 // youtube.com/v/ID
    /(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/,            // youtube.com/shorts/ID
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match && match[1]) {
      return match[1];
    }
  }

  return '';
}
