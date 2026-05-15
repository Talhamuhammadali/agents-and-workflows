"""Snowflake Session builder for llm."""
import json
import os
from typing import Optional

from langchain.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from snowflake.snowpark import Session

from configs.settings import CORTEXT_CLAUDE_SONNET_4_5


def create_snowflake_session(
    account: str,
    user: Optional[str] = None,
    password: Optional[str] = None,
    oauth_token: Optional[str] = None,
    role: Optional[str] = None,
    warehouse: Optional[str] = None,
    database: Optional[str] = None,
    schema: Optional[str] = None,
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
    else:
        params["password"] = password

    for k, v in {"role": role, "warehouse": warehouse,
                 "database": database, "schema": schema}.items():
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
    with open(os.path.expanduser("configs/sf_auth.json")) as f:
        creds = json.load(f)[0]

    # Snowpark resolves the real host; CURRENT_ACCOUNT() drops region/cloud.
    session = create_snowflake_session(**creds)
    host = session._conn._conn.host
    pat = creds["password"]
    session.close()

    return ChatAnthropic(
        anthropic_api_url=f"https://{host}/api/v2/cortex",
        anthropic_api_key="unused",  # pydantic requires a value; auth flows via header
        default_headers={
            "Authorization": f"Bearer {pat}",
            # "anthropic-version": "2023-06-01",
        },
        **CORTEXT_CLAUDE_SONNET_4_5,
    )
