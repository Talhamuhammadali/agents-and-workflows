"""Snowflake Session builder for llm."""

import json
import os

from langchain.chat_models import BaseChatModel
from langchain_anthropic.chat_models import ChatAnthropic
from pydantic import SecretStr
from snowflake.snowpark import Session

from configs.settings import CORTEXT_CLAUDE_SONNET_4_5


def create_snowflake_session(
    account: str,
    user: str | None = None,
    password: str | None = None,
    oauth_token: str | None = None,
    role: str | None = None,
    warehouse: str | None = None,
    database: str | None = None,
    schema: str | None = None,
) -> Session:
    """Create a Snowflake session using OAuth *or* a PAT (exactly one)."""
    if bool(oauth_token) == bool(password):
        raise ValueError("Provide exactly one of `oauth_token` or `password`.")

    params = {"account": account}
    if user:
        params["user"] = user

    if oauth_token:
        params["authenticator"] = "oauth"
        params["token"] = oauth_token
    elif password:
        params["password"] = password
    else:
        raise ValueError("Provide either oauth token or password.")

    for k, v in {"role": role, "warehouse": warehouse, "database": database, "schema": schema}.items():
        if v:
            params[k] = v

    return Session.builder.configs(params).create()


def get_cortext_claude_sonnet_4_5() -> BaseChatModel:
    """Cortex Claude via Snowflake's Anthropic-compatible /v1/messages endpoint.

    `langchain-snowflake` hits the wrong (404) REST path and its SQL path doesn't
    accept `thinking`/`output_config`. The Anthropic-style endpoint at
    `/api/v2/cortex/v1/messages` does — and `ChatAnthropic` already speaks that
    protocol, so we just point it at Snowflake's host.
    """
    cwd = os.getcwd()
    with open(os.path.expanduser(cwd + "/configs/sf_auth.json")) as f:
        creds = json.load(f)[0]

    # Snowpark resolves the real host; CURRENT_ACCOUNT() drops region/cloud.
    session = create_snowflake_session(**creds)
    host = session._conn._conn.host
    pat = creds["password"]
    session.close()

    return ChatAnthropic(
        base_url=f"https://{host}/api/v2/cortex",
        api_key=SecretStr("unused"),  # pydantic requires a value; auth flows via header
        default_headers={
            "Authorization": f"Bearer {pat}",
            # "anthropic-version": "2023-06-01",
        },
        **CORTEXT_CLAUDE_SONNET_4_5,
    )
