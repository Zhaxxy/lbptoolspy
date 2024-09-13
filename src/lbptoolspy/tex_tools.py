from pathlib import Path
import zlib
from io import BytesIO
import struct
from tempfile import TemporaryDirectory
import subprocess
from functools import cache
import logging

from PIL import Image

_TEX_HEADER = b'TEX '
_SOME_FLAG = b'\x00\x01'

@cache
def _check_if_magick_is_installed() -> bool:
    try:
        subprocess.run(('magick', '-version'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        logging.warning('ImageMagick was ethier not installed or not installed correctly, consider installing if you want correct .tex files (LittleBigPlanet) (youll need to restart your scripts after installing it)')
        return False


def image2tex(input_image: Image.Image,/) -> bytes:
    if _check_if_magick_is_installed():
        with TemporaryDirectory() as tp:
            png_path = Path(tp,'umm.dds')
            output_dds_path = Path(tp,'output.dds')
            input_image.save(png_path)
            subprocess.run(('magick', png_path,'-define','dd:mipmaps=1','-define','dds:compression=dtx5',f'DDS:{output_dds_path}'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            dds_bytes = output_dds_path.read_bytes()
    else:
        tex_image = BytesIO()
        input_image.save(tex_image,'dds')
        dds_bytes = tex_image.getvalue()
        del tex_image
        
    return compress_dds_lbp(dds_bytes)


def compress_dds_lbp(dds_bytes: bytes) -> bytes:
    image_chunks = list(dds_bytes[pos:pos + 0x80_00] for pos in range(0, len(dds_bytes), 0x80_00))
    
    data = BytesIO()
    data.write(_TEX_HEADER + _SOME_FLAG + struct.pack('>H',len(image_chunks)))
    
    for i, chunk in enumerate(image_chunks):
        decompressed_size = len(chunk)
        compressed_data = zlib.compress(chunk,level=zlib.Z_BEST_COMPRESSION)
        image_chunks[i] = compressed_data
        
        data.write(struct.pack('>2H',len(compressed_data),decompressed_size))
    
    for compressed_chunk in image_chunks:
        data.write(compressed_chunk)
    
    return data.getvalue()


def tex2image(tex_img: bytes,/) -> Image.Image:
    size_of_magics = len(_TEX_HEADER + _SOME_FLAG)
    data = BytesIO(tex_img)
    header_magic = data.read(size_of_magics)
    if header_magic != (_TEX_HEADER + _SOME_FLAG):
        raise AssertionError(f'Invalid header the tex_img {header_magic}')
    
    image_buffer = BytesIO()
    
    chunk_amnt, = struct.unpack('>H',data.read(2))
    
    chunks_data = [struct.unpack('>2H',data.read(4)) for _ in range(chunk_amnt)]
    
    for compressed_size,decompressed_size in chunks_data:
        image_buffer.write(zlib.decompress(data.read(compressed_size)))
    image_buffer.seek(0)

    return Image.open(image_buffer)


"""
def main():
    hi = Image.open('new_textture.png')
    with open('test.tex','wb') as f: f.write(image2tex(hi))


if __name__ == '__main__':
    main()
"""
