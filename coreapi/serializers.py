from pydantic import BaseModel, Field, conlist, constr
from typing import List, Optional # 引入 Optional

class MergeSchema(BaseModel):
    files: conlist(str, min_length=1) # 使用 conlist 確保至少有一個檔案
    output: str

class SplitSchema(BaseModel):
    file: str
    pages: str # 例如： "1-3,5,!7"
    output_dir: Optional[str] = None # output_dir 是可選的

class AddStampSchema(BaseModel):
    file: str
    page: int # -1 for last page, 1-indexed for others
    stamp_path: str
    pos: Optional[constr(pattern=r'^(tl|tr|bl|br)$')] = 'br' # type: ignore # Allow specific positions
    scale: Optional[float] = 1.0
    output: Optional[str] = None

class RedactSchema(BaseModel):
    file: str
    patterns: conlist(str, min_length=1) # List of regex patterns, at least one
    output: Optional[str] = None

SCHEMAS = {
    "merge": MergeSchema,
    "split": SplitSchema,
    "add_stamp": AddStampSchema,
    "redact": RedactSchema,
} 