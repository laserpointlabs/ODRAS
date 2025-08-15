import asyncio
import logging
from pathlib import Path
from typing import Optional

import httpx

from .config import Settings


logger = logging.getLogger(__name__)


class MicroKernel:
    """
    Development micro-kernel that runs at app startup to:
    - Optionally clear Camunda deployments
    - Auto-deploy BPMN process definitions from the bpmn folder
    - Periodically monitor service status and log health
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._running = False
        self._status_task: Optional[asyncio.Task] = None

        # Derived config
        self.camunda_rest = f"{self.settings.camunda_base_url.rstrip('/')}/engine-rest"

    async def start(self):
        if not self.settings.micro_kernel_enabled:
            logger.info("MicroKernel disabled by settings")
            return

        logger.info("MicroKernel starting...")

        # Optional clear
        if self.settings.micro_kernel_clear_on_start:
            await self._clear_camunda_deployments()

        # Optional auto-deploy
        if self.settings.micro_kernel_autodeploy:
            await self._deploy_all_bpmn_files()

        # Start periodic status logger
        self._running = True
        interval = max(5, self.settings.micro_kernel_status_interval_sec)
        self._status_task = asyncio.create_task(self._status_loop(interval))

    async def stop(self):
        self._running = False
        if self._status_task:
            self._status_task.cancel()
            try:
                await self._status_task
            except asyncio.CancelledError:
                pass

    async def _clear_camunda_deployments(self):
        """Delete all Camunda deployments (dev-only helper)."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # List deployments
                resp = await client.get(f"{self.camunda_rest}/deployment")
                resp.raise_for_status()
                deployments = resp.json() or []
                if not deployments:
                    logger.info("MicroKernel: no Camunda deployments to clear")
                    return
                logger.info(f"MicroKernel: clearing {len(deployments)} Camunda deployments...")
                for d in deployments:
                    dep_id = d.get("id")
                    if not dep_id:
                        continue
                    del_url = f"{self.camunda_rest}/deployment/{dep_id}?cascade=true"
                    try:
                        r = await client.delete(del_url)
                        if 200 <= r.status_code < 300:
                            logger.info(f" - Deleted deployment {dep_id}")
                        else:
                            logger.warning(f" - Failed to delete {dep_id}: {r.status_code}")
                    except Exception as e:
                        logger.warning(f" - Error deleting {dep_id}: {e}")
        except Exception as e:
            logger.warning(f"MicroKernel: failed clearing deployments: {e}")

    async def _deploy_all_bpmn_files(self):
        """Deploy all .bpmn files from configured directory."""
        bpmn_dir = Path(self.settings.micro_kernel_bpmn_dir)
        if not bpmn_dir.exists():
            logger.warning(f"MicroKernel: BPMN dir not found: {bpmn_dir}")
            return

        bpmn_files = sorted(p for p in bpmn_dir.glob("*.bpmn"))
        if not bpmn_files:
            logger.info("MicroKernel: no BPMN files to deploy")
            return

        logger.info(f"MicroKernel: deploying {len(bpmn_files)} BPMN file(s) from {bpmn_dir}")
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                for p in bpmn_files:
                    files = {"file": (p.name, p.read_bytes(), "application/xml")}
                    data = {
                        "deployment-name": f"odras-auto-{p.stem}",
                        "deployment-source": "odras-micro-kernel",
                        "enable-duplicate-filtering": "true",
                        "deploy-changed-only": "true",
                    }
                    try:
                        r = await client.post(f"{self.camunda_rest}/deployment/create", files=files, data=data)
                        if 200 <= r.status_code < 300:
                            logger.info(f" - Deployed {p.name}")
                        else:
                            logger.warning(
                                f" - Failed to deploy {p.name}: {r.status_code} {r.text[:200]}"
                            )
                    except httpx.HTTPError as e:
                        logger.warning(f" - HTTP error deploying {p.name}: {e}")
        except Exception as e:
            logger.warning(f"MicroKernel: error during BPMN deploy: {e}")

    async def _status_loop(self, interval: int):
        """Periodically log service health (Camunda, MinIO)."""
        while self._running:
            try:
                await self._log_status_once()
            except Exception as e:
                logger.debug(f"MicroKernel status loop error: {e}")
            await asyncio.sleep(interval)

    async def _log_status_once(self):
        camunda_status = "unknown"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.camunda_rest}/engine")
                camunda_status = "running" if r.status_code == 200 else f"http {r.status_code}"
        except Exception as e:
            camunda_status = f"unreachable: {e}".split("\n")[0]

        # Future: check MinIO, Qdrant, etc.
        logger.info(f"MicroKernel status: Camunda={camunda_status}")


