"""
Databricks client factories for Spark and Workspace API access.

Provides singleton access to:
- SparkSession (using Databricks Connect or local Spark)
- WorkspaceClient (using databricks-sdk)

Environment variables used:
- DATABRICKS_HOST: Workspace URL
- DATABRICKS_TOKEN: Personal access token (if not using other auth)
- Standard Databricks Connect environment variables
"""

import functools

from databricks.connect import DatabricksSession
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config


def _config() -> Config:
    config = Config()
    if not config.cluster_id and not config.serverless_compute_id:
        config.serverless_compute_id = "auto"
    return config


@functools.cache
def spark() -> DatabricksSession:
    """
    Return a SparkSession, creating one if necessary.

    In Databricks environments (Apps, Notebooks), uses the existing
    session via DatabricksSession. Falls back to local SparkSession
    for development environments.

    Returns:
        Active SparkSession instance.
    """
    return DatabricksSession.builder.sdkConfig(_config()).getOrCreate()


@functools.cache
def workspace_client() -> WorkspaceClient:
    """
    Return a Databricks WorkspaceClient.

    Uses environment-based authentication (DATABRICKS_HOST, DATABRICKS_TOKEN,
    or other configured auth methods like OAuth).

    Returns:
        Configured WorkspaceClient instance.
    """

    return WorkspaceClient(config=_config())
