from pprint import pprint

from agentic_pattern.subagent_pattern.graph import Agent_Builder
from agentic_pattern.subagent_pattern.state import ContextSchema
from utils import MODELS, Model

from langgraph.checkpoint.memory  import InMemorySaver
from langgraph.store.memory import InMemoryStore

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
        all_chunks = []
        for chunk in agent.stream(
            {"message": PROMPT},
            config={"thread_id": f"essay-by-{model.value}"},
            context=context,
            stream_mode=["custom"],
            version="v2",
        ):
            if chunk.get("type") == "custom":
                data = chunk.get("data")
                all_chunks.append(data)
                pprint(data.model_dump(), indent=2)
                
    except Exception as e:
        print(f"  Error: {e}")


def main() -> None:
    for model in MODELS:
        test_graph_with_model(model)


if __name__ == "__main__":
    main()
