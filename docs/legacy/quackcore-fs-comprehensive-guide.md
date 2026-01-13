## QuackCore FS Module Documentation

---

## Table of Contents

1. [Introduction](#introduction)  
2. [Getting Started](#getting-started)  
3. [Core Concepts](#core-concepts)  
   - [Result Objects](#result-objects)  
   - [Error Handling](#error-handling)  
   - [Architecture Overview](#architecture-overview)  
4. [Basic File Operations](#basic-file-operations)  
   - [Reading Files](#reading-files)  
   - [Writing Files](#writing-files)  
   - [Deleting Files](#deleting-files)  
5. [Path Management](#path-management)  
   - [Manipulation](#manipulating-paths)  
   - [Validation & Info](#validation--info)  
   - [Comparison](#comparing-paths)  
6. [Directory Operations](#directory-operations)  
   - [Creating Directories](#creating-directories)  
   - [Listing Contents](#listing-directory-contents)  
   - [Finding Files](#finding-files)  
7. [Structured Data & CSV Utilities](#structured-data--csv-utilities)  
   - [YAML / JSON](#yaml--json-operations)  
   - [CSV File Utilities](#csv-file-utilities)  
8. [Advanced File Operations](#advanced-file-operations)  
   - [Copying & Moving](#copying--moving-files)  
   - [Atomic Operations](#atomic-operations)  
   - [File Information & Checksums](#file-information--checksums)  
   - [Temporary Files & Directories](#temporary-files--directories)  
   - [Disk Usage](#disk-usage)  
9. [Filesystem Utilities](#filesystem-utilities)  
   - [Directory Synchronization](#directory-synchronization)  
   - [File Locking](#file-locking-utility)  
10. [Design Patterns](#design-patterns)  
    - [Facade Pattern](#facade-pattern)  
    - [Strategy Pattern](#strategy-pattern)  
    - [Repository Pattern](#repository-pattern)  
    - [Factory Pattern](#factory-pattern)  
    - [Observer Pattern](#observer-pattern)  
    - [Adapter Pattern](#adapter-pattern)  
    - [Decorator & Error Handling Pattern](#error-handling-pattern)  
11. [Transitioning from `pathlib`](#transitioning-from-pathlib-to-quackcorefs)  
12. [Real-World Examples](#real-world-examples)  
    - [Config File Management](#example-1-config-file-management)  
    - [Log Rotation Tool](#example-2-log-rotation-tool)  
    - [File Backup Tool](#example-3-file-backup-tool)  
13. [Troubleshooting](#troubleshooting)  
    - [Common Issues & Solutions](#common-issues-and-solutions)  
    - [Debugging Tips](#debugging-tips)  
14. [Testing](#testing-with-quackcorefs)  
    - [Mocking the Service](#mocking-the-filesystemservice)  
    - [Fake FileSystemService](#using-a-fake-filesystemservice)  
    - [Pytest Fixture for Temp Dir](#creating-a-test-fixture)  
15. [Integration with QuackCore](#integration-with-quackcore)  
16. [Comparison with Standard Library](#comparison-with-standard-library)  
17. [Best Practices & Pitfalls](#best-practices--common-pitfalls)  
18. [API Reference](#api-reference)  
19. [Conclusion](#conclusion)  

---

## Introduction

The `quack_core.core.fs` module offers a robust, consistent, and developer‑friendly filesystem abstraction for the QuackVerse ecosystem. It standardizes all operations through result objects, improves error handling, and adds advanced features like atomic writes, structured data support, checksums, and more—making it a superior alternative to Python’s built‑in `pathlib`, `os`, and `shutil`.

---

## Getting Started

```python
from quack_core.core.fs import service as fs

# Read text
result = fs.read_text("config.txt")
if result.success:
    print(result.content)
else:
    print(f"Error: {result.error}")

# Write text
fs.write_text("output.txt", "Hello, QuackVerse!")

# Create a directory
fs.create_directory("data", exist_ok=True)
```

---

## Core Concepts

### Result Objects

Every operation returns a standardized result object:

- **OperationResult**: Base class  
  - `success` (bool)  
  - `path` (Path)  
  - `message` / `error` (str)  

- **ReadResult**: adds `content`, `encoding`  
- **WriteResult**: adds `bytes_written`, `checksum`  
- **FileInfoResult**: adds `exists`, `is_file`, `is_dir`, `size`, `modified`, etc.  
- **DirectoryInfoResult**: adds `files`, `directories`, `total_files`, etc.  
- **FindResult**: adds `files`, `directories`, `total_matches`  
- **DataResult**: adds `data`, `format`  
- **PathResult**: for path validation  

### Error Handling

- **Expected errors** (file not found, permission denied) are indicated via `success=False` and `error` message.  
- **Unexpected errors** may still raise exceptions (e.g., invalid parameters).

```python
try:
    result = fs.read_text("missing.txt")
    if not result.success:
        print(f"Could not read: {result.error}")
    else:
        process(result.content)
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Architecture Overview

- **Service Layer**: `FileSystemService` (global `service`)  
- **Mixins**: FileOps, DirOps, StructuredData, PathOps, Validation  
- **Operations**: Internal `_operations`  
- **Helpers**: Atomic writes, checksums  

---

## Basic File Operations

### Reading Files

```python
# Text
text_res = fs.read_text("document.txt")
if text_res.success:
    print(text_res.content)

# Lines
lines_res = fs.read_lines("data.csv")
if lines_res.success:
    for line in lines_res.content:
        print(line)

# Binary
bin_res = fs.read_binary("image.png")
if bin_res.success:
    process(bin_res.content)
```

### Writing Files

```python
# Text
write_res = fs.write_text("log.txt", "Entry", atomic=True)
if write_res.success:
    print(f"Wrote {write_res.bytes_written} bytes")

# Lines
fs.write_lines("data.csv", ["a,b", "c,d"], line_ending="\r\n")

# Binary
with open("orig.bin", "rb") as f:
    data = f.read()
fs.write_binary("copy.bin", data)
```

### Deleting Files

```python
# File or directory
del_res = fs.delete("temp.txt", missing_ok=False)
if not del_res.success:
    print(f"Delete error: {del_res.error}")
```

---

## Path Management

### Manipulating Paths

```python
# Join
join_res = fs.join_path("dir", "sub", "file.txt")
path = join_res.data if join_res.success else None

# Split
split_res = fs.split_path("/a/b/c")
print(split_res.data)  # ['/', 'a', 'b', 'c']

# Normalize
norm_res = fs.normalize_path("x/../y/./z")
print(norm_res.data)

# Expand User/Env
exp_res = fs.expand_user_vars("~/projects")
print(exp_res.data)

# Extension
ext_res = fs.get_extension("file.tar.gz")
print(ext_res.data)  # gz
```

### Validation & Info

```python
# Path info
info = fs.get_path_info("~/docs")
print(info.is_absolute, info.exists)

# Valid syntax
val = fs.is_valid_path("inva|id")
print(val.data)  # False

# Exists
exists = fs.path_exists("file.txt")
print(exists.data)
```

### Comparing Paths

```python
# Same file?
same = fs.is_same_file("a.txt", "./a.txt").data

# Subdirectory?
sub = fs.is_subdirectory("dir/sub", "dir").data
```

---

## Directory Operations

### Creating Directories

```python
# Simple
fs.create_directory("logs", exist_ok=True)

# Nested
fs.create_directory("app/data/cache", exist_ok=True)
```

### Listing Directory Contents

```python
list_res = fs.list_directory("data", pattern="*.json")
print([f.name for f in list_res.files])
print([d.name for d in list_res.directories])
print(f"Total size: {list_res.total_size} bytes")
```

### Finding Files

```python
find_res = fs.find_files("src", "*.py", recursive=True)
for f in find_res.files:
    print(f)

# By content
content_res = fs.find_files_by_content("src", "TODO:")
print(content_res.data)
```

---

## Structured Data & CSV Utilities

### YAML / JSON Operations

```python
# YAML
yaml_res = fs.read_yaml("config.yaml")
if yaml_res.success:
    config = yaml_res.data

fs.write_yaml("config.yaml", { "app": "Q", "version": "1.0" })

# JSON
json_res = fs.read_json("data.json")
if json_res.success:
    data = json_res.data

fs.write_json("data.json", data, indent=2)
```

### CSV File Utilities

```python
from typing import List, Dict, Any, Union

def read_csv(path: str, delimiter: str = ',', has_header: bool = True) -> Union[List[Dict[str,str]], List[List[str]]]:
    result = fs.read_text(path)
    if not result.success:
        raise IOError(f"Read error: {result.error}")
    content = result.content
    from io import StringIO
    import csv
    sio = StringIO(content)
    if has_header:
        reader = csv.DictReader(sio, delimiter=delimiter)
        return list(reader)
    else:
        reader = csv.reader(sio, delimiter=delimiter)
        return list(reader)

def write_csv(path: str, data: Union[List[Dict[str,Any]], List[List[Any]]], fieldnames: List[str]=None, delimiter: str=',') -> bool:
    from io import StringIO
    import csv
    sio = StringIO()
    if data and isinstance(data[0], dict):
        if not fieldnames:
            fieldnames = list(data[0].keys())
        writer = csv.DictWriter(sio, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(data)
    else:
        writer = csv.writer(sio, delimiter=delimiter)
        writer.writerows(data)
    content = sio.getvalue()
    res = fs.write_text(path, content)
    return res.success

def csv_to_json(csv_path: str, json_path: str, delimiter: str = ',') -> bool:
    try:
        data = read_csv(csv_path, delimiter, has_header=True)
        res = fs.write_json(json_path, data, indent=2)
        return res.success
    except Exception as e:
        print(f"Conversion error: {e}")
        return False
```

---

## Advanced File Operations

### Copying & Moving Files

```python
# Copy
cp_res = fs.copy("a.txt", "b.txt", overwrite=True)

# Move
mv_res = fs.move("old.txt", "new.txt", overwrite=False)
```

### Atomic Operations

```python
# Atomic write
atomic_res = fs.atomic_write("critical.txt", "Data")

# Or via write_text/write_yaml/write_json
fs.write_text("safe.txt", "Data", atomic=True)
```

### File Information & Checksums

```python
# Info
info = fs.get_file_info("doc.pdf")
print(info.exists, info.size, info.modified)

# Human-readable size
size_str = fs.get_file_size_str(info.size).data

# MIME type
mime = fs.get_mime_type("image.png").data

# Checksum
chksum = fs.compute_checksum("file.bin", algorithm="md5").data
```

### Temporary Files & Directories

```python
# Temp file
tmpf = fs.create_temp_file(suffix=".log", prefix="qc_").data

# Temp dir
tmpd = fs.create_temp_directory(prefix="qc_").data
```

### Disk Usage

```python
usage = fs.get_disk_usage(".").data
print(f"Total: {fs.get_file_size_str(usage['total']).data}")
```

---

## Filesystem Utilities

### Directory Synchronization

```python
from quack_core.core.fs import service as fs


class DirectorySynchronizer:
    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = source_dir
        self.target_dir = target_dir

    def analyze(self) -> dict:
        src = fs.find_files(self.source_dir, "*", recursive=True)
        tgt = fs.find_files(self.target_dir, "*", recursive=True)
        if not src.success or not tgt.success:
            raise IOError("Failed to list directories")
        src_set = self._rel_paths(src.files, self.source_dir)
        tgt_set = self._rel_paths(tgt.files, self.target_dir)
        to_create = src_set - tgt_set
        to_delete = tgt_set - src_set
        to_update = set()
        for rel in src_set & tgt_set:
            sp = fs.join_path(self.source_dir, rel).data
            tp = fs.join_path(self.target_dir, rel).data
            si = fs.get_file_info(sp)
            ti = fs.get_file_info(tp)
            if si.success and ti.success and si.modified > ti.modified:
                to_update.add(rel)
        return {"create": sorted(to_create), "update": sorted(to_update), "delete": sorted(to_delete)}

    def synchronize(self, delete: bool = False) -> dict:
        diff = self.analyze()
        stats = {"created": 0, "updated": 0, "deleted": 0, "errors": 0}
        # Create, update, delete logic (see full code above)
        return stats

    def _rel_paths(self, paths, base):
        s = set()
        base_str = str(base)
        for p in paths:
            p_str = str(p)
            if p_str.startswith(base_str):
                rel = p_str[len(base_str):].lstrip("/\\")
                s.add(rel)
            else:
                s.add(p_str.split("/")[-1])
        return s
```

### File Locking Utility

```python
from quack_core.core.fs import service as fs
import os, time, random
from datetime import datetime, timedelta


class FileLock:
    def __init__(self, path, timeout=60, retry_delay=0.1):
        self.file_path = path
        self.lock_path = f"{path}.lock"
        self.timeout = timeout
        self.retry = retry_delay
        self.owner = f"{os.getpid()}-{random.randint(1000, 9999)}"
        self.locked = False

    def acquire(self):
        if self.locked: return True
        start = time.time()
        while True:
            if time.time() - start > self.timeout:
                raise TimeoutError("Lock timeout")
            info = self._read_info()
            if info and not self._is_stale(info):
                time.sleep(self.retry)
                continue
            if self._create_lock():
                self.locked = True
                return True
            time.sleep(self.retry)

    def release(self):
        if not self.locked: return
        info = self._read_info()
        if info and info.get("owner") == self.owner:
            fs.delete(self.lock_path)
        self.locked = False

    def _create_lock(self):
        data = {"owner": self.owner, "created": datetime.now().isoformat(), "pid": os.getpid()}
        res = fs.write_json(self.lock_path, data, atomic=True)
        return res.success

    def _read_info(self):
        res = fs.read_json(self.lock_path)
        return res.data if res.success else None

    def _is_stale(self, info):
        try:
            created = datetime.fromisoformat(info["created"])
            return (datetime.now() - created) > timedelta(seconds=self.timeout)
        except:
            return True

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_):
        self.release()
```

---

## Design Patterns

### Facade Pattern

> Simplifies complex filesystem operations.

```python
class FilesystemFacade:
    def ensure_app_directories(self, app_name: str) -> dict:
        dirs = {"config":f"{app_name}/config","data":f"{app_name}/data",
                "logs":f"{app_name}/logs","cache":f"{app_name}/cache","temp":f"{app_name}/temp"}
        created = {}
        for name,path in dirs.items():
            r = fs.create_directory(path, exist_ok=True)
            if r.success: created[name]=str(r.path)
        return created

    def save_config(self, app_name:str, cfg:dict)->bool:
        rd = fs.create_directory(f"{app_name}/config", exist_ok=True)
        if not rd.success: return False
        jp = fs.join_path(f"{app_name}/config","config.yaml")
        if not jp.success: return False
        return fs.write_yaml(jp.data, cfg, atomic=True).success

    def load_config(self, app_name:str)->dict:
        jp = fs.join_path(f"{app_name}/config","config.yaml")
        if not jp.success: return None
        ex = fs.path_exists(jp.data)
        if not ex.success or not ex.data: return None
        rd = fs.read_yaml(jp.data)
        return rd.data if rd.success else None

    def log_message(self, app_name:str, msg:str)->bool:
        logs=f"{app_name}/logs"
        if not fs.create_directory(logs, exist_ok=True).success: return False
        from datetime import datetime
        date_str=datetime.now().strftime("%Y-%m-%d")
        jp=fs.join_path(logs,f"{date_str}.log")
        if not jp.success: return False
        path=jp.data
        ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry=f"[{ts}] {msg}\n"
        ex=fs.path_exists(path)
        if ex.success and ex.data:
            curr=fs.read_text(path).content
            return fs.write_text(path, curr+entry).success
        return fs.write_text(path, entry).success
```

### Strategy Pattern

```python
from abc import ABC, abstractmethod
class StorageStrategy(ABC):
    @abstractmethod
    def save(self,key:str,data:Any)->bool: pass
    @abstractmethod
    def load(self,key:str)->Any: pass
    @abstractmethod
    def delete(self,key:str)->bool: pass
    @abstractmethod
    def exists(self,key:str)->bool: pass

class JsonFileStorage(StorageStrategy):
    def __init__(self,dir:str):
        if not fs.create_directory(dir, exist_ok=True).success:
            raise RuntimeError("Dir error")
        self.dir=dir

    def _path(self,key): return fs.join_path(self.dir,f"{key}.json").data
    def save(self,k,d): return fs.write_json(self._path(k), d, atomic=True).success
    def load(self,k): res=fs.read_json(self._path(k)); return res.data if res.success else None
    def delete(self,k): return fs.delete(self._path(k)).success
    def exists(self,k): return fs.path_exists(self._path(k)).data

class YamlFileStorage(StorageStrategy):
    def __init__(self,dir:str):
        if not fs.create_directory(dir, exist_ok=True).success:
            raise RuntimeError("Dir error")
        self.dir=dir

    def _path(self,key): return fs.join_path(self.dir,f"{key}.yaml").data
    def save(self,k,d): return fs.write_yaml(self._path(k), d, atomic=True).success
    def load(self,k): res=fs.read_yaml(self._path(k)); return res.data if res.success else None
    def delete(self,k): return fs.delete(self._path(k)).success
    def exists(self,k): return fs.path_exists(self._path(k)).data

class DataStorage:
    def __init__(self,strategy:StorageStrategy): self.strategy=strategy
    def set_strategy(self,s:StorageStrategy): self.strategy=s
    def save(self,k,d): return self.strategy.save(k,d)
    def load(self,k): return self.strategy.load(k)
    def delete(self,k): return self.strategy.delete(k)
    def exists(self,k): return self.strategy.exists(k)
```

### Repository Pattern

```python
from typing import TypeVar, Generic, Dict, List, Optional
T = TypeVar('T')

class FileSystemRepository(Generic[T]):
    def __init__(self, base_dir:str, serialize, deserialize):
        if not fs.create_directory(base_dir, exist_ok=True).success:
            raise RuntimeError("Dir error")
        self.base=base_dir; self.ser=serialize; self.deser=deserialize

    def _path(self, id:str):
        return fs.join_path(self.base,f"{id}.json").data

    def save(self, id:str, ent:T)->bool:
        path=self._path(id)
        data=self.ser(ent)
        return fs.write_json(path, data, atomic=True).success

    def get(self, id:str)->Optional[T]:
        path=self._path(id)
        if not fs.path_exists(path).data: return None
        res = fs.read_json(path)
        return self.deser(res.data) if res.success else None

    def delete(self, id:str)->bool:
        return fs.delete(self._path(id)).success

    def list_all(self)->List[T]:
        lst=fs.list_directory(self.base, pattern="*.json")
        ents=[]
        for f in lst.files:
            rd=fs.read_json(f)
            if rd.success:
                ents.append(self.deser(rd.data))
        return ents
```

### Factory Pattern

```python
from quack_core.core.fs import service as fs


class FileHandlerFactory:
    def __init__(self):
        self.handlers = {}

    def register(self, ext, reader, writer):
        self.handlers[ext.lower()] = {'r': reader, 'w': writer}

    def get_reader(self, path):
        ext = fs.get_extension(path).data.lower()
        return self.handlers[ext]['r']

    def get_writer(self, path):
        ext = fs.get_extension(path).data.lower()
        return self.handlers[ext]['w']

    def read(self, path): return self.get_reader(path)(path)

    def write(self, path, data): return self.get_writer(path)(path, data)


# Register
fac = FileHandlerFactory()
fac.register('json',
             reader=lambda p: fs.read_json(p).data,
             writer=lambda p, d: fs.write_json(p, d).success)
fac.register('yaml',
             reader=lambda p: fs.read_yaml(p).data,
             writer=lambda p, d: fs.write_yaml(p, d).success)
fac.register('txt',
             reader=lambda p: fs.read_text(p).content,
             writer=lambda p, d: fs.write_text(p, d).success)
```

### Observer Pattern

```python
from threading import Thread
import time

class FileObserver:
    def __init__(self, interval=5):
        self.files={}, self.cbs={}, self.interval=interval
        self.running=False

    def watch(self,path,callback):
        info=fs.get_file_info(path)
        if not info.success: return False
        meta={'exists':info.exists,'size':info.size,'modified':info.modified}
        self.files[path]=meta
        self.cbs.setdefault(path,[]).append(callback)
        if not self.running: self.start()
        return True

    def unwatch(self,path,callback=None):
        if path not in self.cbs: return
        if callback: self.cbs[path].remove(callback)
        else: del self.cbs[path]
        if not self.cbs: self.stop()

    def start(self):
        self.running=True
        self.thread=Thread(target=self._loop,daemon=True)
        self.thread.start()

    def stop(self):
        self.running=False
        self.thread.join(self.interval+1)

    def _loop(self):
        while self.running and self.cbs:
            self._check()
            time.sleep(self.interval)

    def _check(self):
        for path,meta in list(self.files.items()):
            info=fs.get_file_info(path)
            new={'exists':info.exists,'size':info.size,'modified':info.modified}
            if self._changed(meta,new):
                self.files[path]=new
                for cb in self.cbs[path]:
                    cb(path,new)

    def _changed(self,o,n):
        if o['exists']!=n['exists']: return True
        if not n['exists']: return False
        return o['size']!=n['size'] or o['modified']!=n['modified']
```

### Error Handling Pattern

```python
import logging
from quack_core.core.fs import service as fs

logger = logging.getLogger(__name__)


def safe_read_config(path, default=None):
    if default is None: default = {}
    info = fs.get_file_info(path)
    if not info.success:
        logger.error(f"Info error: {info.error}")
        return default
    if not info.exists:
        logger.warning(f"Missing config: {path}")
        return default
    ext = fs.get_extension(path)
    if not ext.success:
        logger.error(f"Ext error: {ext.error}")
        return default
    if ext.data == 'json':
        rd = fs.read_json(path)
    elif ext.data in ('yml', 'yaml'):
        rd = fs.read_yaml(path)
    else:
        logger.error(f"Unsupported: {ext.data}")
        return default
    if not rd.success:
        logger.error(f"Read error: {rd.error}")
        return default
    return rd.data
```

---

## Transitioning from `pathlib` to `quack_core.core.fs`

| Task                   | `pathlib`                          | `quack_core.core.fs`                                            |
|------------------------|------------------------------------|------------------------------------------------------------|
| Create a path         | `Path("a/b")`                      | `fs.join_path("a","b").data`                              |
| Check exists           | `path.exists()`                    | `fs.path_exists(path).data`                               |
| Read text              | `path.read_text()`                 | `fs.read_text(path).content`                              |
| Write text             | `path.write_text("c")`             | `fs.write_text(path,"c").bytes_written`                   |
| List dir               | `path.iterdir()`                   | `fs.list_directory(path).files + .directories`            |
| Find files             | `path.glob("*.py")`                | `fs.find_files(path,"*.py",recursive=True).files`         |
| Copy                   | `shutil.copy()`                    | `fs.copy(src,dst,overwrite=True)`                         |
| Atomic write           | N/A                                | `fs.atomic_write(path,content)`                           |
| Read YAML / JSON       | External lib + read_text          | `fs.read_yaml(path).data` / `fs.read_json(path).data`      |

---

## Real-World Examples

### Example 1: Config File Management

```python
from quack_core.core.fs import service as fs
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, config_dir="config"):
        rd = fs.create_directory(config_dir, exist_ok=True)
        if not rd.success:
            logger.error(f"Create dir error: {rd.error}")
            raise RuntimeError(rd.error)
        self.dir = rd.path;
        self.settings = {}

    def load(self, name):
        jp = fs.join_path(self.dir, f"{name}.yaml")
        if not jp.success:
            logger.error(jp.error);
            return None
        pi = fs.get_file_info(jp.data)
        if not pi.success or not pi.exists:
            logger.warning("Missing, creating default");
            return self._default(name)
        rd = fs.read_yaml(jp.data)
        if not rd.success:
            logger.error(rd.error);
            return None
        self.settings[name] = rd.data;
        return rd.data

    def save(self, name, data):
        jp = fs.join_path(self.dir, f"{name}.yaml")
        if not jp.success: logger.error(jp.error); return False
        wr = fs.write_yaml(jp.data, data, atomic=True)
        if not wr.success: logger.error(wr.error); return False
        logger.info("Saved");
        return True

    def _default(self, name):
        cfg = {"app": "QuackTool", "version": "1.0", "settings": {"debug": False}}
        self.save(name, cfg)
        return cfg
```

### Example 2: Log Rotation Tool

```python
from quack_core.core.fs import service as fs
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LogRotator:
    def __init__(self, log_dir="logs", max_mb=10, max_logs=5):
        rd = fs.create_directory(log_dir, exist_ok=True)
        if not rd.success: raise RuntimeError(rd.error)
        self.dir = rd.path;
        self.max = max_mb * 1024 * 1024;
        self.limit = max_logs
        self.current = None;
        self._init()

    def _init(self):
        lst = fs.list_directory(self.dir, pattern="*.log")
        files = lst.files if lst.success else []
        if not files: return self._new()
        latest = max(files, key=lambda f: fs.get_file_timestamp(f).data)
        info = fs.get_file_info(latest)
        if info.success and info.size < self.max:
            self.current = latest;
            logger.info(f"Using {latest}")
        else:
            self._new()

    def _new(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        jp = fs.join_path(self.dir, f"app_{ts}.log")
        if not jp.success: raise RuntimeError(jp.error)
        fs.write_text(jp.data, "")
        self.current = jp.data;
        logger.info(f"Created {jp.data}")
        self._cleanup()

    def _cleanup(self):
        lst = fs.list_directory(self.dir, pattern="*.log")
        files = sorted(lst.files, key=lambda f: fs.get_file_timestamp(f).data)
        for old in files[:-self.limit]:
            dr = fs.delete(old)
            if dr.success: logger.info(f"Deleted {old}")

    def write(self, msg):
        if not self.current: self._init()
        entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
        cont = fs.read_text(self.current).content if fs.read_text(self.current).success else ""
        fs.write_text(self.current, cont + entry)
        if fs.get_file_info(self.current).data + len(entry) > self.max:
            logger.info("Rotate");
            self._new()
```

### Example 3: File Backup Tool

```python
from quack_core.core.fs import service as fs
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BackupTool:
    def __init__(self, src, dst, patterns=None):
        self.src, self.dst = src, dst
        self.patterns = patterns or ["*"]
        rd = fs.create_directory(dst, exist_ok=True)
        if not rd.success: raise RuntimeError(rd.error)

    def create_backup(self, checksum=True):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"backup_{ts}"
        jp = fs.join_path(self.dst, name)
        if not jp.success: logger.error(jp.error); return None
        fs.create_directory(jp.data)
        manifest = {"date": ts, "source": str(self.src), "files": []}
        total = 0;
        count = 0
        for pat in self.patterns:
            fr = fs.find_files(self.src, pat, recursive=True)
            for f in fr.files:
                rel = str(f)[len(str(self.src)):].lstrip("/\\")
                # Create dirs
                comps = rel.split("/")
                if len(comps) > 1:
                    pd = fs.join_path(jp.data, *comps[:-1]).data
                    fs.create_directory(pd, exist_ok=True)
                dest = fs.join_path(jp.data, rel).data
                cr = fs.copy(f, dest)
                if cr.success:
                    fi = fs.get_file_info(f);
                    size = fi.size
                    entry = {"path": rel, "size": size}
                    if checksum:
                        ck = fs.compute_checksum(f)
                        if ck.success: entry["checksum"] = ck.data
                    manifest["files"].append(entry)
                    total += size;
                    count += 1
        manifest["total_files"] = count;
        manifest["total_size"] = total
        if fs.get_file_size_str(total).success:
            manifest["human_size"] = fs.get_file_size_str(total).data
        mp = fs.join_path(jp.data, "manifest.json").data
        fs.write_json(mp, manifest, indent=2)
        logger.info(f"Backup done: {count} files, {manifest.get('human_size')}")
        return jp.data

    def verify_backup(self, path):
        mp = fs.join_path(path, "manifest.json").data
        mr = fs.read_json(mp)
        if not mr.success: return False
        files = mr.data.get("files", [])
        ok = 0
        for fe in files:
            dest = fs.join_path(path, fe["path"]).data
            if not fs.get_file_info(dest).data: continue
            if "checksum" in fe:
                ck = fs.compute_checksum(dest)
                if ck.success and ck.data == fe["checksum"]:
                    ok += 1
        integrity = ok / len(files) if files else 0
        logger.info(f"Integrity: {integrity:.1%}")
        return integrity >= 0.99
```

---

## Troubleshooting

### Common Issues and Solutions

1. **Not checking `success`**  
   Always test `result.success` before using result attributes.  
2. **Wrong attribute**  
   - `ReadResult` → `.content`  
   - `DataResult` → `.data`  
3. **Path joining errors**  
   Use `fs.join_path` instead of string concatenation.  
4. **Missing parent dirs**  
   Call `fs.create_directory(parent, exist_ok=True)` first.  
5. **Relative path confusion**  
   Normalize or expand to get absolute paths.

### Debugging Tips

- **Verbose logging**:
  ```python
  from quack_core.core.logging import get_logger, LogLevel
  logger = get_logger(__name__); logger.setLevel(LogLevel.DEBUG)
  ```
- **Inspect full result**:  
  ```python
  res = fs.read_text("f.txt")
  print(res, res.success, res.error)
  ```
- **Test path resolution**:  
  ```python
  n=fs.normalize_path("x/../y"); print(n.data)
  pi=fs.get_path_info(n.data); print(pi)
  ```

---

## Testing with QuackCore FS

### Mocking the FileSystemService

```python
from unittest.mock import patch, MagicMock
from quack_core.core.fs import service as fs
from quack_core.core.fs import DataResult


def read_config(p):
    r = fs.read_yaml(p)
    return r.data if r.success else {}


with patch('quack_core.core.fs.service.read_yaml') as mock_ry:
    mr = MagicMock(spec=DataResult);
    mr.success = True;
    mr.data = {"a": 1}
    mock_ry.return_value = mr
    cfg = read_config("c.yaml")
    assert cfg["a"] == 1
```

### Using a Fake FileSystemService

```python
from quack_core.core.fs import ReadResult, WriteResult, FileInfoResult, DataResult
from pathlib import Path


class FakeFS:
    def __init__(self): self.files = {}

    def read_text(self, p, enc='utf-8'):
        p = str(p)
        if p in self.files:
            return ReadResult(True, Path(p), self.files[p], enc)
        return ReadResult(False, Path(p), "", error="Not found")

    def write_text(self, p, c, enc='utf-8', atomic=False):
        p = str(p);
        self.files[p] = c
        return WriteResult(True, Path(p), len(c.encode(enc)))

    def get_file_info(self, p):
        p = str(p)
        exists = p in self.files
        return FileInfoResult(True, Path(p), exists, exists, False, (len(self.files[p]) if exists else 0), 0)

    def read_yaml(self, p):
        # similar to earlier examples
        ...


# In tests:
fake = FakeFS()
fake.write_text("t.txt", "Hello")


def rl(fs, path):
    r = fs.read_text(path)
    return r.content.split("\n")[0] if r.success else None


assert rl(fake, "t.txt") == "Hello"
```

### Creating a Test Fixture

```python
import pytest
from quack_core.core.fs import service as fs


@pytest.fixture
def temp_dir():
    tr = fs.create_temp_directory()
    if not tr.success: raise RuntimeError("Temp dir error")
    yield tr.data
    fs.delete(tr.data)


def test_file_ops(temp_dir):
    jp = fs.join_path(temp_dir, "file.txt")
    assert fs.write_text(jp.data, "Test").success
    info = fs.get_file_info(jp.data)
    assert info.exists and info.is_file
    assert fs.read_text(jp.data).content == "Test"
    assert fs.delete(jp.data).success
```

---

## Integration with QuackCore

- **Custom Service**:
  ```python
  from quack_core.core.fs import create_service
  fs_service = create_service(base_dir="/app/data")
  ```
- **Plugin**:
  ```python
  from quack_core.core.fs import create_plugin
  fs_plugin = create_plugin()
  ```

---

## Comparison with Standard Library

| Operation              | `pathlib`                                 | `quack_core.core.fs`                                         |
|------------------------|-------------------------------------------|---------------------------------------------------------|
| Read text              | `Path("f.txt").read_text()`               | `fs.read_text("f.txt").content`                        |
| Write text             | `Path("f.txt").write_text("c")`           | `fs.write_text("f.txt","c")`                           |
| Exists                 | `Path.exists()`                           | `fs.path_exists(path).data`                            |
| Create directory       | `Path.mkdir(parents=True,exist_ok=True)`  | `fs.create_directory(path,exist_ok=True)`               |
| List directory         | `list(Path.iterdir())`                    | `fs.list_directory(path).files + .directories`         |
| Find files             | `Path.rglob("*.py")`                      | `fs.find_files(path,"*.py",recursive=True).files`      |
| Copy                   | `shutil.copy(src,dst)`                    | `fs.copy(src,dst,overwrite=True)`                      |
| Atomic write           | N/A                                       | `fs.atomic_write(path,content)`                        |
| Read YAML/JSON         | external lib + `read_text`                | `fs.read_yaml(path).data` / `fs.read_json(path).data`   |

---

## Best Practices & Common Pitfalls

- **Always check `success`** on result objects.  
- **Use type-specific methods** (`read_yaml`, `write_json`).  
- **Join paths** via `fs.join_path`—no manual concatenation.  
- **Ensure parent directories** exist before writing.  
- **Use atomic writes** for critical data.  
- **Handle errors gracefully** via result objects, not only exceptions.  
- **Avoid mixing** direct `os`/`pathlib` calls with `quack_core.core.fs`.  

---

## API Reference

**File Operations**  
- `read_text(path, encoding='utf-8') → ReadResult`  
- `write_text(path, content, encoding='utf-8', atomic=True) → WriteResult`  
- `read_binary(path) → ReadResult`  
- `write_binary(path, content, atomic=True) → WriteResult`  
- `read_lines(path) → ReadResult`  
- `write_lines(path, lines, atomic=True, line_ending='\n') → WriteResult`  
- `delete(path, missing_ok=True) → OperationResult`

**Path Operations**  
- `join_path(*parts) → PathResult`  
- `split_path(path) → PathResult`  
- `normalize_path(path) → PathResult`  
- `expand_user_vars(path) → PathResult`  
- `get_extension(path) → PathResult`  

**Directory Operations**  
- `create_directory(path, exist_ok=True) → WriteResult`  
- `list_directory(path, pattern=None, include_hidden=False) → DirectoryInfoResult`  
- `find_files(path, pattern, recursive=True, include_hidden=False) → FindResult`  
- `find_files_by_content(path, text, recursive=True) → DataResult`

**Structured Data**  
- `read_yaml(path) → DataResult`  
- `write_yaml(path, data, atomic=True) → WriteResult`  
- `read_json(path) → DataResult`  
- `write_json(path, data, atomic=True, indent=2) → WriteResult`

**File Info & Misc**  
- `get_file_info(path) → FileInfoResult`  
- `get_file_size_str(size_bytes) → PathResult`  
- `get_mime_type(path) → PathResult`  
- `get_file_timestamp(path) → PathResult`  
- `compute_checksum(path, algorithm='sha256') → PathResult`  
- `atomic_write(path, content) → DataResult`  
- `create_temp_file(...) → PathResult`  
- `create_temp_directory(...) → PathResult`  
- `get_disk_usage(path) → DataResult`  

---

## Conclusion

`quack_core.core.fs` streamlines and enhances filesystem interactions with:

- **Consistent result objects** for all operations  
- **Advanced features**: atomic writes, structured data, checksums, disk usage  
- **Clear error handling** and logging integration  
- **Powerful patterns** for real‑world tasks  

Adopting `quack_core.core.fs` ensures safer, more maintainable, and feature‑rich filesystem code in your QuackTools. Happy coding in the QuackVerse!