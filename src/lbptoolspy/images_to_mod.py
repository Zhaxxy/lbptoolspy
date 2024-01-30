from typing import Sequence
from PIL import Image
from zipfile import ZipFile
from pathlib import Path

def images_to_mod(the_images: Sequence[Path], output_mod: ZipFile):
    raise NotImplementedError