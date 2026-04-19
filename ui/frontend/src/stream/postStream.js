// POST + SSE streaming. Events are `data: {json}\n\n` blocks;
// `onEvent` fires once per parsed event.

export async function streamPost(url, body, onEvent) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Stream failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    // SSE events are separated by blank lines.
    const blocks = buf.split("\n\n");
    buf = blocks.pop(); // keep the trailing partial for the next chunk
    for (const block of blocks) {
      const data = parseEventData(block);
      if (data) onEvent(data);
    }
  }
  const tail = parseEventData(buf);
  if (tail) onEvent(tail);
}

// Collects `data:` lines from an SSE event block, joins them, and parses JSON.
// Returns null if the block has no data lines.
function parseEventData(block) {
  const dataLines = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
  }
  if (!dataLines.length) return null;
  return JSON.parse(dataLines.join("\n"));
}
