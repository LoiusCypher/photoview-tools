from enum import Enum

class Tags(Enum):
    hosts = "Hosts"
    actions = "Actions"
    ignores = "Ignores"
    folders = "Folders"
    files = "Files"
    current = "Current host"
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

