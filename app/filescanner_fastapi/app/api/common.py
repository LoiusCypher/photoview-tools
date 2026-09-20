from enum import Enum


class Tags(Enum):
    current = "00 Current Host"
    hosts   = "A1 Hosts"
    actions = "A2 Actions"
    ignores = "A3 Ignores"
    folders = "A4 Folders"
    files   = "A5 Files"
    admin   = "B1 Admin Tools"
    pathlist= "C1 Path Lists"
    develop = "Development"

class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"

class SortIgnoreField(str, Enum):
    host_id = "host_id"
    path_pattern = "path_pattern"
    created_at = "created_at"
    updated_at = "updated_at"

class SortActionField(str, Enum):
    host_id = "host_id"
    subtree = "subtree"
    started_at = "started_at"
    created_at = "created_at"
    updated_at = "updated_at"
    deleted_at = "deleted_at"

class SortFolderField(str, Enum):
    host_id = "host_id"
    parent_id = "parent_id"
    path = "path"
    path_hash = "path_hash"
    depth = "depth"
    created_at = "created_at"
    updated_at = "updated_at"
    deleted_at = "deleted_at"

class SortFileField(str, Enum):
    folder_id = "folder_id"
    file_name = "file_name"
    length = "length"
    ctime_ns = "ctime_ns"
    mtime_ns = "mtime_ns"
    file_hash = "file_hash"
    created_at = "created_at"
    updated_at = "updated_at"
    deleted_at = "deleted_at"

