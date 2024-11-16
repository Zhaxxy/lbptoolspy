import tempfile
import subprocess
from pathlib import Path
import json

from .binary_files import JSONINATOR_ARGS

_PathlibPathOrStringPath = str | Path

class BaseLbpFileParseError(Exception):
    """
    Do not raise, only catch, and use as a base
    """

class LbpNormalFileParseError(BaseLbpFileParseError):
    """
    Raise if a lbp file is bad
    """

class LbpJsonFileParseError(BaseLbpFileParseError):
    """
    Raise if a lbp json file is bad (dict)
    """

test_result = subprocess.run(JSONINATOR_ARGS,capture_output=True)
if test_result.returncode:
    raise Exception(f'something went wrong with jsoninator... {test_result.stderr!r}') 
del test_result

def lbpfile2json(lbp_file: _PathlibPathOrStringPath | bytes | bytearray, write_to_json_file: _PathlibPathOrStringPath | None = None) -> dict:
    with tempfile.TemporaryDirectory() as tp:
        temp_lbp_file = Path(tp,'a.b')
        
        if isinstance(lbp_file,(bytes,bytearray)):
            temp_lbp_file.write_bytes(lbp_file)
        else:
            temp_lbp_file = Path(lbp_file)
        
        temp_json = Path(tp,'b.json')
        if write_to_json_file:
            temp_json = Path(write_to_json_file)
        
        test_result = subprocess.run(JSONINATOR_ARGS + (temp_lbp_file,temp_json),capture_output = True, shell=False)
        if test_result.returncode or test_result.stderr:
            raise LbpNormalFileParseError(f'something went wrong parsing the lbp file... {test_result.stderr!r}') 
        
        result = json.loads(temp_json.read_text())
    
    return dict(result)


def json2lbpfile(json_file: _PathlibPathOrStringPath | dict, write_to_lbp_file: _PathlibPathOrStringPath | None = None) -> bytes:
    with tempfile.TemporaryDirectory() as tp:
        temp_json = Path(tp,'a.json')
        
        if isinstance(json_file,dict):
            temp_json.write_text(json.dumps(json_file))
        else:
            if isinstance(json_file,str) and json_file.strip().endswith('}'):
                temp_json.write_text(json_file)
            else:
                temp_json = Path(json_file)
        
        temp_lbp = Path(tp,'b.b')
        if write_to_lbp_file:
            temp_lbp = Path(write_to_lbp_file)
        
        test_result = subprocess.run(JSONINATOR_ARGS + (temp_json,temp_lbp),capture_output = True, shell=False)
        if test_result.returncode or test_result.stderr:
            raise LbpJsonFileParseError(f'something went wrong parsing the json lbp file... {test_result.stderr!r}') 
        
        return temp_lbp.read_bytes()
