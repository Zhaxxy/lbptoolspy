"""
code based on https://github.com/ennuo/toolkit/tree/dc82bee57ab58e9f4bf35993d405529d4cbc7d00
"""
import hashlib
from pathlib import Path
import struct
from typing import BinaryIO, NamedTuple, Iterator

_REVISION_LM_MAX = 0x6
_LM_HEAD = 0x01ae03fa
_USE_ALL_COMPRESSION = 7


class InvalidOldFormatMod(Exception):
    pass


class _ToolkitFakeItem:
    pass


class _ToolkitSha1(NamedTuple):
    bytes_value: bytes
    
    @classmethod
    def from_bytes(cls,sha1_bytes: bytes) -> '_ToolkitSha1':
        if len(sha1_bytes) != 20:
            raise ValueError(f'sha1 should be 20 bytes long, not {len(sha1_bytes)}')
        return cls(bytes_value = sha1_bytes)


class _ModEntry(NamedTuple):
    path: Path
    size: int
    guid: int
    date: int


def number_in_chunks(total_bytes: int, chunk_size: int = 2 * 1024 * 1024) -> Iterator[int]:
    while total_bytes > chunk_size:
        yield chunk_size
        total_bytes -= chunk_size
    if total_bytes:
        yield total_bytes


def _get_version_from_revision(revision: int) -> int:
    return revision & 0xFFFF


def _read_uleb128(stream: BinaryIO) -> int:
    """
    https://chatgpt.com/share/69e4ff8d-2978-8390-8060-35eb10f2e974
    """
    result = 0
    shift = 0

    while True:
        try:
            byte = stream.read(1)[0]
        except IndexError:
            raise EOFError("Unexpected end of stream while reading ULEB128")

        result |= (byte & 0x7F) << shift

        if (byte & 0x80) == 0:
            break

        shift += 7

    return result

def _toolkit_read_enum32(stream: BinaryIO,signed: bool = False) -> int:
    """
    https://github.com/ennuo/toolkit/blob/dc82bee57ab58e9f4bf35993d405529d4cbc7d00/lib/cwlib/src/main/java/cwlib/io/streams/MemoryInputStream.java#L623
    """
    if signed:
        return _toolkit_read_i32(stream)
    else:
        return _toolkit_read_u32(stream)

def _toolkit_read_i16(stream: BinaryIO) -> int:
    return int.from_bytes(stream.read(2),'big',signed=True)

def _toolkit_read_u16(stream: BinaryIO) -> int:
    return _toolkit_read_i16(stream) & 0xFFFF

def _toolkit_read_sha1(stream: BinaryIO) -> _ToolkitSha1:
    return _ToolkitSha1.from_bytes(stream.read(20))

def _toolkit_read_guid(stream: BinaryIO) -> int:
    # this is basically all this does
    return _toolkit_read_u32(stream)

def _toolkit_read_u32(stream: BinaryIO) -> int:
    return _read_uleb128(stream)

def _toolkit_read_i32(stream: BinaryIO) -> int:
    return _read_uleb128(stream) & 0xFFFFFFFF

def _toolkit_read_f32(stream: BinaryIO) -> float:
    """
    toolkit calls `_toolkit_read_i32` with force32 be true, so that it returns big endian 4 bytes
    """
    res = struct.unpack('>f',stream.read(4))[0]
    assert isinstance(res,float)
    return res

def _toolkit_read_v4(stream: BinaryIO) -> tuple[float,float,float,float]:
    return (_toolkit_read_f32(stream),_toolkit_read_f32(stream),_toolkit_read_f32(stream),_toolkit_read_f32(stream))

def _toolkit_read_m44(stream: BinaryIO) -> list[list[float]]:
    flat = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    ]

    compression_flags = _USE_ALL_COMPRESSION
    USE_COMPRESSED_MATRICES = 4
    
    flags = 0xFFFF
    if (compression_flags & USE_COMPRESSED_MATRICES) != 0:
        flags = _toolkit_read_i16(stream)

    for i in range(16):
        if (flags & (1 << i)) != 0:
            flat[i] = _toolkit_read_f32(stream)

    # Convert to 4x4
    return [flat[i:i+4] for i in range(0, 16, 4)]

def _toolkit_read_s64(stream: BinaryIO) -> int:
    # exact same as _toolkit_read_s32, force64 will always be false
    return _toolkit_read_s32(stream)

def _toolkit_read_s32(stream: BinaryIO) -> int:
    v = _read_uleb128(stream)
    return (v >> 1 ^ -(v & 1))

def _toolkit_read_str_with_length(stream: BinaryIO,length: int) -> str:
    return stream.read(length).replace(b'\x00',b'').decode('utf-8')
def _toolkit_read_str(stream: BinaryIO) -> str:
    string_length = _toolkit_read_s32(stream)
    return _toolkit_read_str_with_length(stream,string_length)

def _toolkit_read_wstr_with_length(stream: BinaryIO,length: int) -> str:
    return stream.read(length*2).decode('utf-16BE')
def _toolkit_read_wstr(stream: BinaryIO) -> str:
    string_length = _toolkit_read_s32(stream)
    return _toolkit_read_wstr_with_length(stream,string_length)


def _read_slot_array(mod_file: BinaryIO, refrence_ids: set[int] | None = None) -> _ToolkitFakeItem:
    count = _toolkit_read_i32(mod_file)
    if count != 0:
        raise InvalidOldFormatMod('Yeahh, aint no way im parsing this https://github.com/ennuo/toolkit/blob/dc82bee57ab58e9f4bf35993d405529d4cbc7d00/lib/cwlib/src/main/java/cwlib/structs/slot/Slot.java#L167')
    return _ToolkitFakeItem()


def _read_photo_user_array(mod_file: BinaryIO, refrence_ids: set[int] | None = None) -> _ToolkitFakeItem:
    count = _toolkit_read_i32(mod_file)
    for _ in range(count):
        # PhotoUser
        if refrence_ids is not None:
            ref_id = _toolkit_read_i32(mod_file)
            if ((ref_id != 0) and (ref_id not in refrence_ids)) or refrence_ids is None:
                psid = _toolkit_read_wstr_with_length(mod_file,0x14)
                user = _toolkit_read_str(mod_file)
                bounds = _toolkit_read_v4(mod_file)
                if refrence_ids is not None:
                    refrence_ids.add(ref_id)
    return _ToolkitFakeItem()

def _read_painting_resource(mod_file: BinaryIO,is_descripter: bool = True) -> _ToolkitFakeItem:
    return _read_resource(mod_file,53,is_descripter)

def _read_icon_resource(mod_file: BinaryIO,is_descripter: bool = True) -> _ToolkitFakeItem:
    return _read_resource(mod_file,1,is_descripter)

def _read_resource(mod_file: BinaryIO,resource_type: int,is_descripter: bool = True) -> _ToolkitFakeItem:
    # look into https://github.com/ennuo/toolkit/blob/dc82bee57ab58e9f4bf35993d405529d4cbc7d00/lib/cwlib/src/main/java/cwlib/io/serializer/Serializer.java#L784
    # the types https://github.com/ennuo/toolkit/blob/dc82bee57ab58e9f4bf35993d405529d4cbc7d00/lib/cwlib/src/main/java/cwlib/enums/ResourceType.java#L14
        cp = True
        t = False
        
        hash_constant = 1
        guid_constant = 2
        
        if _get_version_from_revision(_LM_HEAD) < 0x191 and cp:
            hash_constant = 2
            guid_constant = 1
        
        flags = 0
        
        if _get_version_from_revision(_LM_HEAD) > 0x22e and not is_descripter:
            flags = _toolkit_read_i32(mod_file)
        
        guid_hash_flag = int.from_bytes(mod_file.read(1),signed=True)
        
        guid: int | None = None
        hash: _ToolkitSha1 | None = None
        
        if guid_hash_flag & guid_constant != 0:
            guid = _toolkit_read_guid(mod_file)
        if guid_hash_flag & hash_constant != 0:
            hash = _toolkit_read_sha1(mod_file)
        
        if t:
            resource_type = _toolkit_read_i32(mod_file)
        
        # dont need to continue further
        return _ToolkitFakeItem()


def _read_inventory_item_details(mod_file: BinaryIO,refrence_ids: set[int]) -> _ToolkitFakeItem:
    head = _get_version_from_revision(_LM_HEAD)
    if _get_version_from_revision(_LM_HEAD) > 0x37c:
        date_added = _toolkit_read_s64(mod_file)
        # SlotID
        slot_type = _toolkit_read_enum32(mod_file)
        slot_number = _toolkit_read_u32(mod_file)
        highlight_sound = _toolkit_read_guid(mod_file)
        colour = _toolkit_read_i32(mod_file)
        
        # get type https://github.com/ennuo/toolkit/blob/dc82bee57ab58e9f4bf35993d405529d4cbc7d00/lib/cwlib/src/main/java/cwlib/structs/inventory/InventoryItemDetails.java#L152
        _toolkit_read_i32(mod_file)
        
        sub_type = _toolkit_read_i32(mod_file)
        title_key = _toolkit_read_u32(mod_file)
        description_key = _toolkit_read_u32(mod_file)
        
        # https://github.com/ennuo/toolkit/blob/dc82bee57ab58e9f4bf35993d405529d4cbc7d00/lib/cwlib/src/main/java/cwlib/structs/inventory/InventoryItemDetails.java#L160 -> https://github.com/ennuo/toolkit/blob/dc82bee57ab58e9f4bf35993d405529d4cbc7d00/lib/cwlib/src/main/java/cwlib/io/serializer/Serializer.java#L1078
        # CreationHistory
        ref_id = _toolkit_read_i32(mod_file)
        if (ref_id != 0) and (ref_id not in refrence_ids):
            if_fixed = _get_version_from_revision(_LM_HEAD) > 0x37c
            creators_count = _toolkit_read_i32(mod_file)
            for _ in range(creators_count):
                if if_fixed:
                    _toolkit_read_str_with_length(mod_file,0x14)
                else:
                    _toolkit_read_wstr(mod_file)
            
            refrence_ids.add(ref_id)
        
        # at https://github.com/ennuo/toolkit/blob/dc82bee57ab58e9f4bf35993d405529d4cbc7d00/lib/cwlib/src/main/java/cwlib/structs/inventory/InventoryItemDetails.java#L162
        
        icon = _read_icon_resource(mod_file)
        
        # UserCreatedDetails
        ref_id = _toolkit_read_i32(mod_file)
        if (ref_id != 0) and (ref_id not in refrence_ids):
            name = _toolkit_read_wstr(mod_file)
            description = _toolkit_read_wstr(mod_file)
            refrence_ids.add(ref_id)
        

        # InventoryItemPhotoData
        ref_id = _toolkit_read_i32(mod_file)
        if (ref_id != 0) and (ref_id not in refrence_ids):
            photo_icon = _read_icon_resource(mod_file)
            sticker = _read_icon_resource(mod_file)
            
            # PhotoMetadata
            photo = _read_icon_resource(mod_file)
            # SlotID
            slot_type = _toolkit_read_enum32(mod_file)
            slot_number = _toolkit_read_u32(mod_file)
            
            level_name = _toolkit_read_wstr(mod_file)
            level_hash = _toolkit_read_sha1(mod_file)
            timestamp = _toolkit_read_s64(mod_file)
            
            _read_photo_user_array(mod_file)
            
            if _get_version_from_revision(_LM_HEAD) > 0x37c:
                _read_painting_resource(mod_file)
            refrence_ids.add(ref_id)


        # EyetoyData
        ref_id = _toolkit_read_i32(mod_file)
        if (ref_id != 0) and (ref_id not in refrence_ids):
            if _get_version_from_revision(_LM_HEAD) > 0x15e:
                frame = _read_icon_resource(mod_file)
                alpha_mask = _read_icon_resource(mod_file)
                _toolkit_read_m44(mod_file)

                # ColorCorrection colorCorrectionSrc
                saturation = _toolkit_read_f32(mod_file)
                hueShift = _toolkit_read_f32(mod_file)
                brightness = _toolkit_read_f32(mod_file)
                contrast = _toolkit_read_f32(mod_file)
                tintHue = _toolkit_read_f32(mod_file)
                tintAmount = _toolkit_read_f32(mod_file)
            refrence_ids.add(ref_id)


        location_index = _toolkit_read_i16(mod_file)
        category_index = _toolkit_read_i16(mod_file)
        primary_index = _toolkit_read_i16(mod_file)

        # NetworkPlayerID
        ref_id = _toolkit_read_i32(mod_file)
        if (ref_id != 0) and (ref_id not in refrence_ids):
            # NetworkOnlineID
            length_prefixed = _get_version_from_revision(_LM_HEAD) < 0x234
            if length_prefixed:
                #https://github.com/ennuo/toolkit/blob/dc82bee57ab58e9f4bf35993d405529d4cbc7d00/lib/cwlib/src/main/java/cwlib/types/data/NetworkOnlineID.java#L37
                _toolkit_read_i32(mod_file)
            data = mod_file.read(16)
            term = int.from_bytes(mod_file.read(1))
            assert term == 0
            if length_prefixed:
                _toolkit_read_i32(mod_file)
                
            dummy = mod_file.read(3)
            
            length_prefixed = _get_version_from_revision(_LM_HEAD) < 0x234
            if length_prefixed:
                _toolkit_read_i32(mod_file)
            opt = mod_file.read(8)
            
            if length_prefixed:
                _toolkit_read_i32(mod_file)
            reserved = mod_file.read(8)
            
            refrence_ids.add(ref_id)
        
        # toolType,flags
        mod_file.seek(1*2,1)
    else:
        raise AssertionError(f'only implemtned for {_LM_HEAD}')
    return _ToolkitFakeItem()


def extract_old_craftworld_toolkit_mod_format(mod_file: BinaryIO, output_folder: Path, *, flat_dir: bool = False, use_file_hashes_as_paths: bool = False) -> None:
    if use_file_hashes_as_paths:
        raise NotImplementedError('Need to figure out how to hash in chunks to get the filename')
    header = mod_file.read(4)
    if header != b'MODb':
        if header == b'PK\x03\x04':
            raise InvalidOldFormatMod('Mod seems to be a new format mod (has PK.. header)')
        else:
            raise InvalidOldFormatMod('Mod doesnt have MODb header, most likely invalid')
    revision = int.from_bytes(mod_file.read(1))
    if revision != 6:
        raise InvalidOldFormatMod(f'Currently only supports revision {hex(_REVISION_LM_MAX)}, yours is {hex(revision)}')
    
    mod_file.seek(1,1) # Skip compatibility
    
    config_version = f'{int.from_bytes(mod_file.read(1))}.{int.from_bytes(mod_file.read(1))}'
    config_id = _toolkit_read_str(mod_file)
    config_author = _toolkit_read_wstr(mod_file)
    config_title = _toolkit_read_wstr(mod_file)
    config_description = _toolkit_read_wstr(mod_file)
    
    entry_count = _toolkit_read_i32(mod_file)
    mod_entries = []
    for _ in range(entry_count):
        path = Path(_toolkit_read_str(mod_file))
        size = _toolkit_read_i32(mod_file)
        guid = _toolkit_read_guid(mod_file)
        date = _toolkit_read_u32(mod_file)
        # https://github.com/ennuo/toolkit/blob/dc82bee57ab58e9f4bf35993d405529d4cbc7d00/lib/cwlib/src/main/java/cwlib/types/mods/Mod.java#L213
        # since we only care about extracting im just gonna ignore this
        mod_entries.append(_ModEntry(path,size,guid,date))
    
    # https://github.com/ennuo/toolkit/blob/dc82bee57ab58e9f4bf35993d405529d4cbc7d00/lib/cwlib/src/main/java/cwlib/types/mods/Mod.java#L221
    
    ref_ids: set[int] = set()
    
    item_count = _toolkit_read_i32(mod_file)
    for _ in range(item_count):
        _read_inventory_item_details(mod_file,ref_ids)
        _toolkit_read_u32(mod_file)
        _toolkit_read_u32(mod_file) # location/category
        
        _read_resource(mod_file,38)
        _toolkit_read_wstr(mod_file)
        _toolkit_read_wstr(mod_file) # translatedLocation/Category
        
        _toolkit_read_i32(mod_file)
        _toolkit_read_i32(mod_file) # min/max revisions

    _read_slot_array(mod_file)

    patch_count = _toolkit_read_i32(mod_file)
    for _ in range(patch_count):
        patch_type = int.from_bytes(mod_file.read(1),signed=False)
        tag = _toolkit_read_str(mod_file)
        _toolkit_read_i32(mod_file) # lams key id
        value = _toolkit_read_wstr(mod_file)
    
    # now we are beyond the bullcrap, we can extract the mod
    for i,(path,size,_,_) in enumerate(mod_entries):
        if flat_dir:
            new_path = output_folder / f'{i}_{path.as_posix().replace("/",f"_")}'
        else:
            new_path.parent.mkdir(exist_ok=True)
            new_path = output_folder / path
        
        with new_path.open('wb') as f:
            for chunk_size in number_in_chunks(size):    
                f.write(mod_file.read(chunk_size))

