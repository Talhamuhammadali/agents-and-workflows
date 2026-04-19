// Fold a flat MessageResponse[] (from the history API or SSE stream) into
// the shape the UI already renders:
//
//   [
//     { type: "human", content },
//     { type: "ai", id, name, content_blocks: [...] },
//     { type: "tool", tool_call_id, name, content },
//     ...
//   ]
//
// Events with the same `id` extend the same AI message. Content blocks —
// reasoning, text, tool_call — are appended to `content_blocks` in arrival
// order so the UI renders them exactly as emitted. Tool results key on their
// originating call id (see docs/sse-streaming.md).

export function accumulate(events) {
  const messages = [];
  const argsBuffer = {}; // call_id -> raw JSON, for partial streaming args

  const findAi = (id) => messages.find((m) => m.type === "ai" && m.id === id);
  const toolCallBlockIndex = (ai, callId) =>
    ai.content_blocks.findIndex(
      (b) => b.type === "tool_call" && b.call.id === callId
    );

  for (const ev of events) {
    const { id, role_type, message_type, content, name } = ev;

    if (role_type === "human") {
      messages.push({ type: "human", content });
      continue;
    }

    if (role_type === "tool_result") {
      // Tool outputs can stream — same id extends the existing tool message.
      const existing = messages.find(
        (m) => m.type === "tool" && m.tool_call_id === id
      );
      if (existing) {
        existing.content = (existing.content ?? "") + content;
      } else {
        messages.push({ type: "tool", tool_call_id: id, name, content });
      }
      // Point the owning AI message's liveKey at the tool_call block whose
      // result is currently streaming in.
      const owner = messages.find(
        (m) => m.type === "ai" && toolCallBlockIndex(m, id) !== -1
      );
      if (owner) {
        owner.liveKey = { kind: "block", index: toolCallBlockIndex(owner, id) };
      }
      continue;
    }

    if (role_type !== "ai") continue; // notification/etc — handled elsewhere

    let ai = findAi(id);
    if (!ai) {
      ai = { type: "ai", id, name, content_blocks: [] };
      messages.push(ai);
    }

    if (message_type === "reasoning" || message_type === "text") {
      const key = message_type;
      let block = ai.content_blocks.at(-1);
      if (!block || block.type !== key) {
        block = { type: key, [key]: "" };
        ai.content_blocks.push(block);
      }
      block[key] += content;
      ai.liveKey = { kind: "block", index: ai.content_blocks.length - 1 };
      continue;
    }

    if (message_type === "tool_call") {
      const callId = typeof content === "object" ? content.id : id;
      let idx = toolCallBlockIndex(ai, callId);
      if (idx === -1) {
        ai.content_blocks.push({
          type: "tool_call",
          call: { id: callId, name: "", args: {} },
        });
        idx = ai.content_blocks.length - 1;
      }
      const call = ai.content_blocks[idx].call;
      if (typeof content === "string") {
        argsBuffer[callId] = (argsBuffer[callId] || "") + content;
        try { call.args = JSON.parse(argsBuffer[callId]); } catch {}
      } else {
        Object.assign(call, content);
      }
      ai.liveKey = { kind: "block", index: idx };
    }
  }

  return messages;
}
