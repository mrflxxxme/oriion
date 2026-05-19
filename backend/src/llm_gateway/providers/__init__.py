"""Provider implementations for llm_gateway.

Each provider conforms to ``src.llm_gateway.providers.base.LLMProvider``
Protocol so the router can hold a single ``dict[str, LLMProvider]`` keyed
by provider_slug.
"""
