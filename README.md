# ExpiringDictx

<div align="center">

[![codecov](https://codecov.io/gh/AzideCupric/expiringdictx/graph/badge.svg?token=879N3D5BJK)](https://codecov.io/gh/AzideCupric/expiringdictx)
[![Build Status](https://img.shields.io/github/actions/workflow/status/AzideCupric/expiringdictx/test.yml?branch=main)](https://github.com/AzideCupric/expiringdictx/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/expiringdictx.svg)](https://badge.fury.io/py/expiringdictx)
[![Python version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/AzideCupric/expiringdictx)](https://github.com/AzideCupric/expiringdictx/blob/main/LICENSE)

</div>

---

## 简介 | Introduction

这是一个带有过期时间的字典数据结构，适用于缓存和临时存储。  
This is a dictionary data structure with an expiration time, suitable for caching and temporary storage.

## 安装 | Install

### 使用 pip 安装 | Install with pip

```bash
pip install expiringdictx
```

### 使用 poetry 安装 | Install with poetry

```bash
poetry add expiringdictx
```

### 使用 pdm 安装 | Install with pdm

```bash
pdm add expiringdictx
```

## 使用 | Usage

### ExpiringDict

```python
from datetime import timedelta
from expiringdictx import ExpiringDict

# 创建一个 ExpiringDict 实例 | Create an ExpiringDict instance
cache = ExpiringDict[str, str](capacity=100, default_age=60)

# 添加一个元素，过期时间为默认值 | Add an item with the default expiration time
cache["key0"] = "value0"
# 添加一个元素，过期时间为 30 秒 | Add an item with an expiration time of 30 seconds
cache["key1", 30] = "value1"
# 添加一个元素，过期时间为 2 分钟 | Add an item with an expiration time of 2 minutes
cache["key2", timedelta(minutes=2)] = "value2"
# 或者使用 set 方法 | Or use the set method
cache.set("key3", "value3", 60)

# 获取一个元素 | Get an item
value0 = cache["key0"]
value1 = cache.get('key1')
# 获取时附带过期时间 | Get with expiration time
value2, deadtime2 = cache.get_with_deadtime('key2')

# 获取并删除一个元素 | pop an item
value3 = cache.pop('key3')
value4 = cache.popitem(least_recently=True)

# 获取元素ttl(剩余存活时间) | Get the ttl(time to live) of an item
ttl = cache.ttl('key0')
# 获取元素ddl(过期时间) | Get the ddl(deadline) of an item
ddl = cache.ddl('key0')

# 按照给定keys创建一个新的ExpiringDict | Create a new ExpiringDict with the given keys
new_cache = cache.fromkeys(['key0', 'key1', 'key2'], "default_value", 60)
# 按照给定可映射对象创建一个新的ExpiringDict | Create a new ExpiringDict with the given mapping
new_cache = cache.frommapping({'key0': 'value0', 'key1': ('value1', 1), 'key2': ('value2', timedelta(hours=2))}, 60)
# 从另一个ExpiringDict创建一个新的ExpiringDict | Create a new ExpiringDict from another ExpiringDict
new_cache = cache.fromexpiringdict(cache, 60)
```

## 测试 | Tests

运行单元测试： | Run the unit tests:

```bash
pytest tests/
```

## 致谢 | Thanks

[`lru-dict`](https://github.com/amitdev/lru-dict): ExpiringDict 的内部存储实现  
[`expiringdict`](https://github.com/mailgun/expiringdict): 本项目的灵感来源，在此基础上添加类型注解和其他功能

## 许可 | License

MIT

---
