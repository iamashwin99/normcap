"""Handler to store images as files. Intended for debugging purposes."""

# Default
import pathlib
import datetime

# Own
from handlers.abstract_handler import AbstractHandler
from data_model import NormcapData


class StoreHandler(AbstractHandler):
    def handle(self, request: NormcapData) -> NormcapData:
        """Store all screenshots and selection on harddrive.

        Arguments:
            AbstractHandler {class} -- self
            request {NormcapData} -- NormCap's session data

        Returns:
            NormcapData -- Enriched NormCap's session data
        """
        if request.cli_args["path"]:
            self._logger.info(f"Saving images to {request.cli_args['path']}...")
            all_images = [request.image] + [s["image"] for s in request.shots]
            self.store_images(request.cli_args["path"], all_images)

        if self._next_handler:
            return super().handle(request)
        else:
            return request

    def store_images(self, path: str, images: list):
        """Save images on harddrive.

        Arguments:
            path {str} -- Target directory
            images {list} -- Images to store
        """
        storage_path = pathlib.Path(path)
        now = datetime.datetime.now()

        for idx, image in enumerate(images):
            name = f"{now:%Y-%m-%d_%H:%M}_{idx}.png"
            image.save(storage_path / name)