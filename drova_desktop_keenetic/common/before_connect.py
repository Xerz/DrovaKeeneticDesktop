import logging
import os
from asyncio import sleep

from asyncssh import SSHClientConnection, SFTPNoSuchFile

from drova_desktop_keenetic.common.commands import ShadowDefenderCLI, TaskKill
from drova_desktop_keenetic.common.contants import (
    SHADOW_DEFENDER_DRIVES,
    SHADOW_DEFENDER_PASSWORD,
)
from drova_desktop_keenetic.common.patch import ALL_PATCHES

logger = logging.getLogger(__name__)


class BeforeConnect:
    logger = logger.getChild("BeforeConnect")

    def __init__(self, client: SSHClientConnection):
        self.client = client

    async def run(self) -> bool:

        self.logger.info("open sftp")
        try:
            async with self.client.start_sftp_client() as sftp:

                self.logger.info(f"start shadow")
                # start shadow mode
                await self.client.run(
                    str(
                        ShadowDefenderCLI(
                            password=os.environ[SHADOW_DEFENDER_PASSWORD],
                            actions=["enter"],
                            drives=os.environ[SHADOW_DEFENDER_DRIVES],
                        )
                    )
                )
                await sleep(2)

                for patch in ALL_PATCHES:
                    self.logger.info(f"prepare {patch.NAME}")
                    try:
                        if patch.TASKKILL_IMAGE:
                            await self.client.run(str(TaskKill(image=patch.TASKKILL_IMAGE)))
                        await sleep(0.2)
                        patcher = patch(self.client, sftp)
                        await patcher.patch()

                    except SFTPNoSuchFile as e:
                        self.logger.warning(f"Файл не найден при применении патча {patch.NAME}: {e}")

                    except Exception as e:
                        self.logger.exception(f"Ошибка при выполнении патча {patch.NAME}: {e}")

                await sleep(1)

                # Запускаем obs (через скомпилированный ahk-скрипт)
                self.client.run(str(PsExec(command="str.exe")), check=False)

        except Exception:
            logger.exception("We have problem")
        return True
