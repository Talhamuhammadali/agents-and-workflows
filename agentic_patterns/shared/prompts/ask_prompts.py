"""Prompt for an ask question tool allowing agent to ask the user a question and get a response."""
ASK_TOOL_DESCRIPTION = """Use this tool when you want to ask the user a question and get their response. \
The question should be specific and clear, so the user can provide a helpful answer.\
The user's response will be provided in the next turn as a human message in the conversation history.

There are two types of questions you can ask:

- Multiple choice: Provide a list of options for the user to choose from with final option as open-ended auto injected.
- Open-ended: Ask a question that allows the user to respond in their own words.

The reponse will be a string with following format:
Q1: <question>
<user's answer or selected option>
Q2: <question>
<user's answer or selected option>
...

"""