"""Structural guarantees for workspace data source onboarding.

Two concerns, both asserted statically or against pure in-process
construction (no live database needed -- that part is proven for real in
tests/integration/test_datasource_*.py):

1. Nothing in ``app.datasources`` reaches the LLM provider or the demo
   connection's own global singletons -- onboarding is infrastructure, not an
   agent capability, and it must never share mutable state with the
   process-wide demo/global analytics stack.
2. Every collaborator this feature *extended* rather than duplicated
   (``AnalyticsDatabase``, ``PostgreSQLQueryValidator``,
   ``AnalyticsSchemaPolicy``, ``MetricRegistry``) still behaves exactly as it
   did before when called the old way -- "existing demo database
   compatibility" is a property of the demo path never having to change, not
   just a claim in a docstring.
"""

from __future__ import annotations

import ast
import inspect
from collections import deque
from pathlib import Path

import pytest

from tests.support import BACKEND_ROOT

APP = BACKEND_ROOT / "app"


def _module_path(name: str) -> Path | None:
    base = BACKEND_ROOT / name.replace(".", "/")
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _imports(name: str) -> set[str]:
    path = _module_path(name)
    if path is None:
        return set()
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names if alias.name.startswith("app.")}
    return found


def _reachable(start: str) -> set[str]:
    seen: set[str] = set()
    queue = deque([start])
    while queue:
        name = queue.popleft()
        if name in seen:
            continue
        seen.add(name)
        queue.extend(_imports(name))
    return seen


# -- 1. isolation from the LLM and from the demo connection's global state --


@pytest.mark.parametrize(
    "module",
    [
        "app.datasources.contracts", "app.datasources.encryption", "app.datasources.security",
        "app.datasources.store", "app.datasources.runtime", "app.datasources.connectivity",
        "app.datasources.profiling", "app.datasources.freshness", "app.datasources.service",
        "app.datasources.governed_inspector", "app.datasources.governed_query_tool",
        "app.datasources.tool_integration",
    ],
)
def test_no_datasources_module_reaches_the_llm_provider(module: str) -> None:
    reachable = _reachable(module)

    assert module in reachable
    llm_reachable = [name for name in reachable if name.startswith("app.llm")]
    assert not llm_reachable, f"{module} can reach the LLM provider package via {llm_reachable}"


def test_the_data_source_store_and_service_never_import_the_demo_connections_singletons() -> None:
    """A workspace connection must build its own engine, never reuse the process-wide demo one."""

    direct_imports = _imports("app.composition.providers.datasources")
    forbidden = {
        "app.composition.providers.analytics",  # get_analytics_database() etc. -- the demo/global engine
    }
    offending = direct_imports & forbidden
    assert not offending, f"app.composition.providers.datasources reaches the demo connection via {offending}"


def test_metric_execution_is_not_wired_into_the_governed_tool_set() -> None:
    """Out of scope for this phase: MetricRegistry stays hand-authored against the demo schema only."""

    direct_imports = _imports("app.datasources.tool_integration")
    assert "app.analytics.semantics.metrics" not in direct_imports


# -- 2. every extended (not duplicated) collaborator is unchanged by default --


def test_analytics_database_without_connect_args_behaves_as_before() -> None:
    from app.analytics.connection import AnalyticsDatabase

    database = AnalyticsDatabase("postgresql+asyncpg://user:pass@localhost/db")

    assert database._connect_args == {}


def test_analytics_database_signature_still_accepts_only_a_url_positionally() -> None:
    """The pre-existing single-argument call every other caller already uses must keep working."""

    from app.analytics.connection import AnalyticsDatabase

    signature = inspect.signature(AnalyticsDatabase.__init__)
    parameters = list(signature.parameters.values())
    assert parameters[1].name == "database_url"
    assert parameters[1].default is inspect.Parameter.empty
    assert parameters[2].name == "connect_args"
    assert parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters[2].default is None


def test_query_validator_without_excluded_columns_validates_exactly_as_before() -> None:
    from app.analytics.schema.allowlist import AnalyticsSchemaPolicy
    from app.analytics.sql.validator import PostgreSQLQueryValidator

    policy = AnalyticsSchemaPolicy.configured("public")
    validator = PostgreSQLQueryValidator(policy)

    result = validator.validate("SELECT id FROM orders", allowed_tables=["orders"])

    assert result.valid is True


def test_the_single_schema_configured_helper_is_untouched() -> None:
    """for_schemas() is new plumbing for a workspace's multi-schema list; configured() is the original."""

    from app.analytics.schema.allowlist import AnalyticsSchemaPolicy

    policy = AnalyticsSchemaPolicy.configured("public")

    assert policy.allowed_schemas == frozenset({"public"})


def test_for_schemas_refuses_an_empty_list() -> None:
    from app.analytics.schema.allowlist import AnalyticsSchemaPolicy

    with pytest.raises(ValueError):
        AnalyticsSchemaPolicy.for_schemas([])


def test_metric_registry_still_takes_no_workspace_or_connection_argument() -> None:
    """Generalizing metric execution to an arbitrary workspace schema is explicitly out of scope."""

    from app.analytics.semantics.metrics import MetricRegistry

    signature = inspect.signature(MetricRegistry.__init__)
    assert set(signature.parameters) == {"self", "definitions"}
