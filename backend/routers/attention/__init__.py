"""Attention Stewardship / 守心 API (package).

Mechanically split from the original single-file ``routers/attention.py`` (~4500 lines)
into functional submodules. All routes are registered on the single shared
``router`` (defined in ``_common``) in the exact same order as the original file,
and every module-level symbol of the original module is re-exported here, so
``from routers.attention import router, init_attention_router, ...`` keeps working
unchanged.

NOTE: the legacy ``routers/attention.py`` file may still exist on disk; Python
gives this package precedence over the same-named module, so this package is the
one actually imported. The legacy file can be deleted (``git rm``) safely.
"""
# Import order matters: submodules register their routes on the shared router
# at import time, and this order reproduces the original file's route order.
from . import _common
from . import _models
from . import covenant
from . import focus
from . import admin
from . import reports
from . import _social
from . import accountability
from . import groups
from . import diagnosis
from . import warfare

router = _common.router
init_attention_router = _common.init_attention_router

# Re-export every module-level name of the original single-file module
# (public and private alike) to keep external imports, tests and
# monkeypatch-style access working.
for _mod in (_common, _models, covenant, focus, admin, reports, _social,
             accountability, groups, diagnosis, warfare):
    for _name, _value in vars(_mod).items():
        if _name.startswith('__'):
            continue
        globals().setdefault(_name, _value)
del _mod, _name, _value
