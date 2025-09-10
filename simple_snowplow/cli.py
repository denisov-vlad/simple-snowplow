"""Command Line Interface for simple-snowplow.

Usage examples (from project root):

# Print settings as pretty JSON
uv run simple_snowplow/cli.py settings
# Print raw pydantic Settings object repr
uv run simple_snowplow/cli.py settings --raw
# Fire attribute traversal (prints common.hostname)
uv run simple_snowplow/cli.py settings hostname
# Create ClickHouse databases & tables
uv run simple_snowplow/cli.py db init
# Download tracker scripts (sp.js + plugins)
uv run simple_snowplow/cli.py scripts download

The `db init` command replaces the previous automatic table creation that
occurred during FastAPI lifespan startup.
"""

from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import fire
import orjson
import requests
import structlog
from clickhouse_connect import get_async_client
from clickhouse_connect.driver.exceptions import ClickHouseError, DatabaseError
from clickhouse_connect.driver.httputil import get_pool_manager
from core.config import settings
from plugins.logger import init_logging
from routers.tracker.db.clickhouse import ClickHouseConnector, TableManager


class SettingsCommands:
    """Settings related commands.

    Exposes the pydantic Settings model through Fire. Returning native Python
    structures keeps output composable (e.g., you can pipe to jq if JSON).
    """

    def __init__(self) -> None:
        # Use cached global settings instance
        self._settings = settings

    def __call__(
        self,
        raw: bool = False,
        indent: int = 2,
    ) -> Any:  # pragma: no cover - thin wrapper
        """Print full settings.

        Parameters
        ----------
        raw : bool, default False
                If True, return the raw pydantic Settings object representation.
                Otherwise output JSON (pretty by default) so it's shell-friendly.
        indent : int, default 2
                JSON indentation (ignored when raw=True).
        """
        if raw:
            return self._settings
        return orjson.dumps(
            self._settings.model_dump(mode="json"),
            indent=indent,
            sort_keys=True,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return settings as a plain dict (no JSON serialization)."""
        return self._settings.model_dump(mode="json")

    def hostname(self) -> str:
        """Convenience accessor for common.hostname (demonstrates attribute path)."""
        return str(self._settings.common.hostname)


class DBCommands:
    """Database (ClickHouse) related commands."""

    logger = structlog.get_logger("cli.db")

    def init(self) -> str:
        """Create required ClickHouse databases and tables.

        Replaces automatic table creation previously executed during FastAPI lifespan.
        """

        async def _run():
            init_logging(settings.logging.json_format, settings.logging.level)
            perf_conf = settings.performance
            ch_conf = settings.clickhouse

            pool_mgr = get_pool_manager(maxsize=perf_conf.db_pool_size)

            try:
                client = await get_async_client(
                    **ch_conf.connection.model_dump(),
                    query_limit=0,
                    pool_mgr=pool_mgr,
                )
            except (
                ClickHouseError,
                DatabaseError,
            ) as e:  # pragma: no cover - network path
                self.logger.error("Failed to connect to ClickHouse", error=str(e))
                raise

            try:
                connector = ClickHouseConnector(
                    client,
                    **ch_conf.configuration.model_dump(),
                )
                table_manager = TableManager(connector)
                await table_manager.create_all_tables()
                self.logger.info("ClickHouse initialization complete")
            finally:
                await client.close()

        asyncio.run(_run())
        return "ClickHouse initialization complete"


class CLI:
    """Root CLI object.

    Additional top-level commands can be added as new attributes or methods.
    """

    def __init__(self) -> None:  # pragma: no cover - trivial wiring
        self.settings = SettingsCommands()
        self.db = DBCommands()
        self.scripts = ScriptsCommands()


class ScriptsCommands:
    """Manage static tracker scripts (download/update)."""

    logger = structlog.get_logger("cli.scripts")

    def download(
        self,
        version: str = "4.6.6",
        output_dir: str = "static",
        force: bool = False,
        create_loader_copy: bool = True,
    ) -> str:
        """Download Snowplow JS tracker bundle and plugins.

        Parameters
        ----------
        version : str
                Release version tag of snowplow-javascript-tracker.
        output_dir : str
                Directory to place downloaded artifacts.
        force : bool
                Redownload even if version marker exists.
        create_loader_copy : bool
                Whether to duplicate sp.js -> loader.js (legacy naming in project).
        """
        base_url = f"https://github.com/snowplow/snowplow-javascript-tracker/releases/download/{version}"
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        marker_file = out_path / f"VERSION_{version}"
        if marker_file.exists() and not force:
            result = f"Scripts already present for version {version}. "
            result += "Use --force to redownload."
            return result

        files = ["sp.js", "sp.js.map", "plugins.umd.zip"]
        for filename in files:
            url = f"{base_url}/{filename}"
            self.logger.info("Downloading", url=url)
            resp = requests.get(url, timeout=60)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Failed to download {filename}: HTTP {resp.status_code}",
                )
            (out_path / filename).write_bytes(resp.content)

        # Unzip plugins
        zip_path = out_path / "plugins.umd.zip"
        with ZipFile(BytesIO(zip_path.read_bytes())) as zf:
            zf.extractall(out_path)
        zip_path.unlink(missing_ok=True)

        # Duplicate loader copies if requested
        if create_loader_copy:
            for base in ["sp.js", "sp.js.map"]:
                src = out_path / base
                if src.exists():
                    dest = out_path / base.replace("sp.js", "loader.js")
                    dest.write_bytes(src.read_bytes())

            # Adjust source map file field so it references loader.js
            loader_map = out_path / "loader.js.map"
            if loader_map.exists():
                orig_text = loader_map.read_text(encoding="utf-8")
                updated_text: str | None = None
                data = orjson.loads(orig_text)
                data["file"] = "loader.js"
                updated_text = orjson.dumps(data).decode("utf-8")
                loader_map.write_text(updated_text, encoding="utf-8")
                self.logger.info("Updated loader.js.map file field to loader.js")

        # Write version marker (empty file used as flag)
        for old_marker in out_path.glob("VERSION_*"):
            if old_marker.name != marker_file.name:
                old_marker.unlink()  # clean previous markers
        marker_file.touch(exist_ok=True)

        return f"Downloaded tracker scripts version {version} to {out_path}"


def main() -> None:  # pragma: no cover - Fire dispatch
    fire.Fire(CLI())


if __name__ == "__main__":  # pragma: no cover
    main()
