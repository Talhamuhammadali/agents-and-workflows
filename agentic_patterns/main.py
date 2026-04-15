from agentic_pattern.subagent_pattern.graph import Agent_Builder
from agentic_pattern.subagent_pattern.state import ContextSchema
from langchain_core.messages import AIMessageChunk
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from utils import MODELS, Model

TOPIC = "Why curiosity is humanity's greatest superpower"
PROMPT = f"Write a 100-word essay file on: {TOPIC}. \
    add a section at the end which is seprate from the main essay explaining you thought process. "


def test_graph_with_model(model: Model) -> None:
    """Test the graph with a specific model, printing chunks and final block types."""
    print(f"\n{'=' * 60}")
    print(f"Testing graph with: {model.value}")
    print(f"{'=' * 60}")

    context = ContextSchema(agent_name="essay-writer", model=model, subagents=[])
    agent = Agent_Builder.compile(checkpointer=InMemorySaver(), store=InMemoryStore())
    try:
        messages: list[AIMessageChunk] = []
        current_message: AIMessageChunk | None = None
        current_id: str | None = None
        for chunk in agent.stream(  # type: ignore[call-overload]
            {"message": PROMPT},
            config={"configurable": {"thread_id": f"essay-by-{model.value}"}},
            context=context,
            stream_mode=["custom", "messages"],
            version="v2",
        ):
            if chunk.get("type") == "custom":
                data = chunk.get("data")
                chunk_id = data.id
                if chunk_id != current_id:
                    if current_message is not None:
                        print(f"\n{'─' * 40} end of {current_id}\n")
                        messages.append(current_message)
                    current_id = chunk_id
                    current_message = data
                    print(f"{'─' * 40} new message: {chunk_id}")
                else:
                    current_message += data

            if chunk.get("type") == "messages":
                print(f"\n{'─' * 40} new message chunk\n")
                print(f"Chunk content: {type(chunk.get('data'))}")
                print(f"Chunk content: {len(chunk.get('data'))}")
                print(f"Chunk content: {chunk.get('data')[1]}")
        if current_message is not None:
            messages.append(current_message)

        print(f"\n{'=' * 40}")
        print(f"Total messages: {len(messages)}")
        for msg_id, msg in enumerate(messages):
            print(f"\n  [{msg_id}] tool_calls: {[tc['name'] for tc in msg.tool_calls] if msg.tool_calls else 'none'}")

    except Exception as e:
        print(f"  Error: {e}")


def main() -> None:
    for model in MODELS:
        test_graph_with_model(model)


if __name__ == "__main__":
    main()
