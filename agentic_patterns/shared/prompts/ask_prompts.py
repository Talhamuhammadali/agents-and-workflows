"""Prompt for an ask question tool allowing agent to ask the user a question and get a response."""
ASK_TOOL_DESCRIPTION = """Use this tool when you want to ask the user a question and get their response. \
The question should be specific and clear, so the user can provide a helpful answer.\
The user's response will be provided in the next turn as a human message in the conversation history.

There are two types of questions you can ask:

- Multiple choice: Provide a list of options for the user to choose from with final option as open-ended auto injected.
- Open-ended: Ask a question that allows the user to respond in their own words.


Example call:
{
  "questions": [
    {
      "question": "Which database should we target for the new pipeline?",
      "options": ["Postgres", "BigQuery", "Snowflake"]
    },
    {
      "question": "What's the refresh cadence?",
      "options": ["Hourly", "Daily"]
    },
    {
      "question": "Any retention constraints we should know about?"
    }
  ]
}

The response will be a string with the following format:

Q1: Which database should we target for the new pipeline?
Postgres

Q2: What's the refresh cadence?
Hourly

Q3: Any retention constraints we should know about?
Keep raw data for 90 days, aggregates forever.
"""