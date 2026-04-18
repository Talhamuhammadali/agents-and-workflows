# SSE Streaming Integration

How streamed `AgentResponse` events map into the UI's accumulated message state.

## Event shape

Incoming events match the backend `AgentResponse` schema:

```python
class AgentResponse(BaseModel):
    id: str                              # merge key — same id extends same block
    checkpoint_id: Optional[str]
    message_type: MessageTypes           # reasoning | text | tool_call | ...
    role_type: Literal["ai", "human", "tool_result"]
    subtype: Optional[str]               # artifact type, when role produces one
    content: Union[str, Dict, List]      # payload — shape depends on message_type
    name: Optional[str]
    last_message: Optional[str]          # "True" / "False"
    status: str
    thread_id: str
    timestamp: str
```

## Flow

```
SSE events  →  accumulator  →  UI state (messages[])  →  components render
```

The UI renders the **accumulated** state (same shape as `ui/frontend/src/data/dummy.js`).
The accumulator sits between the transport and React state; it's the only thing that
understands events.

## Event → state mapping

| role_type | message_type  | content shape        | Action on state                                                     |
| --------- | ------------- | -------------------- | ------------------------------------------------------------------- |
| `human`   | —             | `str`                | push new `{ type: "human", content }` message                       |
| `ai`      | `reasoning`   | `str` (chunk)        | find/create AI message by `id`, extend its `reasoning` block        |
| `ai`      | `text`        | `str` (chunk)        | find/create AI message by `id`, extend its `text` block             |
| `ai`      | `tool_call`   | `dict` or `str`      | upsert into `tool_calls[]` of current AI message (see partial args) |
| `tool`    | —             | `str`                | push `{ type: "tool", content, tool_call_id, name }`                |
| `updates` | —             | `dict` (state patch) | apply to `todos` / `workspace` / `artifact` (non-message state)     |

Messages are merged by `id`: consecutive events with the same `id` extend the same message.

## Handling partial vs complete tool_call args

Some providers stream tool_call args as partial JSON strings; others send the whole
dict in one event. The accumulator handles both:

```js
if (typeof event.content === "string") {
  // streaming partial JSON
  buffer[event.id] += event.content;
  try {
    toolCall.args = JSON.parse(buffer[event.id]);
  } catch {
    // keep last successful parse; renderers must tolerate missing keys
  }
} else {
  // complete dict — merge directly
  toolCall = { ...toolCall, ...event.content };
}
```

Renderers already default missing keys (`args?.path ?? ""`) so partial state renders
gracefully — the user sees content fill in as the stream arrives.

## Accumulator sketch

```js
// ui/frontend/src/stream/accumulator.js  (not yet implemented)

export function createAccumulator() {
  const state = { messages: [], todos: [], workspace: [], artifact: null };
  const argsBuffer = {}; // tool_call_id -> raw JSON string

  function findAiMessage(id) {
    return state.messages.find((m) => m.type === "ai" && m.id === id);
  }

  function apply(event) {
    const { role_type, message_type, content, id } = event;

    if (role_type === "human") {
      state.messages.push({ type: "human", content });
      return;
    }

    if (role_type === "tool") {
      state.messages.push({
        type: "tool",
        tool_call_id: id,            // tool events carry the originating call id
        content,
        name: event.name,
      });
      return;
    }

    if (role_type === "updates") {
      Object.assign(state, content);  // state patch
      return;
    }

    // role_type === "ai"
    let msg = findAiMessage(id);
    if (!msg) {
      msg = { type: "ai", id, name: event.name, content_blocks: [], tool_calls: [] };
      state.messages.push(msg);
    }

    if (message_type === "reasoning" || message_type === "text") {
      const key = message_type;           // "reasoning" | "text"
      let block = msg.content_blocks.at(-1);
      if (!block || block.type !== key) {
        block = { type: key, [key]: "" };
        msg.content_blocks.push(block);
      }
      block[key] += content;
    }

    if (message_type === "tool_call") {
      const callId = typeof content === "object" ? content.id : id;
      let call = msg.tool_calls.find((t) => t.id === callId);
      if (!call) {
        call = { id: callId, name: "", args: {}, type: "tool_call" };
        msg.tool_calls.push(call);
      }
      if (typeof content === "string") {
        argsBuffer[callId] = (argsBuffer[callId] || "") + content;
        try { call.args = JSON.parse(argsBuffer[callId]); } catch {}
      } else {
        Object.assign(call, content);
      }
    }
  }

  return { state, apply };
}
```

## Wiring into React

```js
// ui/frontend/src/App.jsx  (sketch)

const [state, setState] = useState(initialState);

useEffect(() => {
  const acc = createAccumulator();
  const es = new EventSource(`/api/stream?thread_id=${threadId}`);

  es.onmessage = (e) => {
    acc.apply(JSON.parse(e.data));
    setState({ ...acc.state });              // shallow clone to trigger re-render
  };

  return () => es.close();
}, [threadId]);
```

Components already render from the accumulated `state` — no changes needed.

## Open questions

- **`MessageTypes` enum**: need the full list so the accumulator's `message_type`
  branches are exhaustive. Current plan covers `reasoning`, `text`, `tool_call`.
  If there's `artifact`, `status`, `error`, add explicit branches.
- **`updates` content shape**: confirm it's a partial state patch vs. a full replacement.
  The sketch assumes `Object.assign(state, content)` — adjust if nested merge is needed.
- **Tool result linking**: schema doesn't have a dedicated `tool_call_id` field.
  The sketch assumes `event.id` on a `tool` role IS the originating tool_call id.
  Confirm or specify where the link lives.
- **`subtype`**: not yet handled — likely feeds artifact rendering when the agent
  produces one. Map subtypes to artifact renderers once the values are known.
- **Auto-scroll**: chat panel should scroll to bottom on new events during streaming,
  but only if the user is already near the bottom (don't hijack their scroll).

## Checklist for wire-up

- [ ] Confirm `MessageTypes` enum values
- [ ] Confirm `updates` content shape and `tool` ↔ `tool_call` linking
- [ ] Add `src/stream/accumulator.js` from sketch above
- [ ] Add EventSource/SSE hook in `App.jsx`
- [ ] Add auto-scroll behavior to `ChatPanel`
- [ ] Verify renderers tolerate partial args (spot-check write_file, edit_file, bash)
- [ ] Drop `src/data/dummy.js` import once live events work end-to-end
