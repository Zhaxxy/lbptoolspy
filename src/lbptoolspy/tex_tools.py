import zlib
from io import BytesIO
import struct

from PIL import Image

_TEX_HEADER = b'TEX '
_SOME_FLAG = b'\x00\x01'


def image2tex(input_image: Image.Image,/) -> bytes:
    tex_image = BytesIO()
    input_image.save(tex_image,'dds')
    
    return compress_dds_lbp(tex_image.getvalue())


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


"""
def main():
    hi = Image.open('new_textture.png')
    with open('test.tex','wb') as f: f.write(image2tex(hi))


if __name__ == '__main__':
    main()
"""
