// Fold a flat MessageResponse[] (from the history API or SSE stream) into
// the shape the UI already renders:
//
//   [
//     { type: "human", content },
//     { type: "ai", id, name, content_blocks: [...], tool_calls: [...] },
//     { type: "tool", tool_call_id, name, content },
//     ...
//   ]
//
// Events with the same `id` extend the same AI message. Tool results use
// their own `id` as the tool_call_id link (see docs/sse-streaming.md).

export function accumulate(events) {
  const messages = [];
  const argsBuffer = {}; // call_id -> raw JSON, for partial streaming args

  const findAi = (id) => messages.find((m) => m.type === "ai" && m.id === id);

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
      // The owning AI message is still "live" on this tool until something
      // else updates it — point its liveKey at the streaming call.
      const owner = messages.find(
        (m) => m.type === "ai" && m.tool_calls?.some((t) => t.id === id)
      );
      if (owner) owner.liveKey = { kind: "tool", callId: id };
      continue;
    }

    if (role_type !== "ai") continue; // notification/etc — handled elsewhere

    let ai = findAi(id);
    if (!ai) {
      ai = { type: "ai", id, name, content_blocks: [], tool_calls: [] };
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
      let call = ai.tool_calls.find((t) => t.id === callId);
      if (!call) {
        call = { id: callId, name: "", args: {}, type: "tool_call" };
        ai.tool_calls.push(call);
      }
      if (typeof content === "string") {
        argsBuffer[callId] = (argsBuffer[callId] || "") + content;
        try { call.args = JSON.parse(argsBuffer[callId]); } catch {}
      } else {
        Object.assign(call, content);
      }
      ai.liveKey = { kind: "tool", callId };
    }
  }

  return messages;
}
