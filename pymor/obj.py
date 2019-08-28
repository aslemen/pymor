import attr
import typing

import pathlib
import importlib.util as imputil

import collections
import pygtrie

import itertools
import functools

import ruamel.yaml as yaml

@attr.s(
    slots = True,
    cmp = True,
    frozen = True,
    cache_hash = True
)
class Entry:
    phon = attr.ib(
        cmp = True,
        kw_only = True,
        type = str
    ) 
    feat = attr.ib(
        cmp = True,
        factory = frozenset,
        kw_only = True,
        type = typing.FrozenSet[typing.Tuple[str, typing.Any]]
    )
    sem = attr.ib(
        cmp = True,
        factory = lambda: "",
        kw_only = True,
        type = str
    )
    gloss = attr.ib(
        cmp = True,
        factory = lambda: "",
        kw_only = True,
        type = str
    )

    yaml_tag = "!e"

    def __str__(self) -> str:
        return "{{{phon}:{sem}#({hash:X})}}".format(
            phon = self.phon,
            sem = self.sem,
            hash = hash(self)
        )
    # === END ===

    @classmethod
    def to_yaml(
        cls, 
        representer, 
        node: "Entry"
    ) -> yaml.nodes.MappingNode :
        return representer.represent_mapping(
            tag = cls.yaml_tag,
            mapping = {
                "phon": node.phon,
                "feat": dict(node.feat),
                "sem": node.sem,
                "gloss": node.gloss
            }
        )
    # === END ===

    @classmethod
    def from_yaml(
        cls, 
        constructor: yaml.constructor.Constructor, 
        node: yaml.nodes.MappingNode
    ) -> "Entry":
        dict_actual = yaml.comments.CommentedMap()

        constructor.construct_mapping(node, dict_actual)

        if "feat" in dict_actual:
            dict_actual["feat"] = frozenset(
                dict_actual["feat"].items()
            )
        # === END IF ===
        return cls(**dict_actual)
    # === END ===
# === END CLASS ===

@attr.s(
    slots = True,
    cmp = False,
)
class Model:
    name = attr.ib(
        repr = True,
        init = True,
        default = "<UNTITLED>",
        kw_only = True,
        type = str,
    )

    source_dir = attr.ib(
        repr = False,
        init = True,
        default = "<UNKNOWN>",
        kw_only = True,
        type = typing.Union[str, "pathlib.Path"]
    )

    ext_src = attr.ib(
        repr = False,
        init = True,
        default = "",
        kw_only = True,
        type = str
    )

    _entries = attr.ib(
        repr = False,
        init = False,
        factory = pygtrie.CharTrie,
        type = pygtrie.CharTrie
    )

    def __getitem__(self, key: str) -> typing.Iterator[Entry]:
        return iter(self._entries.get(key, iter()))
    # === END ===

    def __iter__(self) -> typing.Iterator[Entry]:
        return itertools.chain.from_iterable(
            self._entries.values()
        )
    # === END ===

    def __len__(self) -> int:
        return len(self._entries)
    # === END ===

    def keys(self) -> typing.Iterator[str]:
        return self._entries.keys()
    # === END ===

    def has_key(self, key: str) -> bool:
        return self._entries.has_key(str)
    # === END ===
    
    def clear_caches(self) -> typing.NoReturn:
        self.tokenize.cache_clear()
    # === END ===

    def _add(self, entry: Entry) -> typing.NoReturn:
        phon = entry.phon

        if phon not in self._entries:
            self._entries[phon] = set((entry, ))
        else:
            self._entries[phon].add(entry)
        # === END IF ===
    # === END ===

    def add(self, entry: Entry) -> typing.NoReturn:
        self._add(entry)
        self.clear_caches()
    # === END ===

    def batchadd(self, entries: typing.Iterable[Entry]) -> typing.NoReturn:
        for entry in entries: 
            self._add(entry)
        self.clear_caches()
    # === END ===

    def delete(self, entry: Entry) -> typing.NoReturn:
        phon = entry.phon
        
        if phon in self._entries:
            self._entries[phon].discard(entry)
            self.clear_caches()
        # === END IF ===
    # === END ===

    def merge(
        self,
        other: "Model"
    ):
        self._entries.update(other._entries)
        self.clear_caches()
    # === END ===

    @classmethod
    def union(
        cls,
        *dicts: typing.List["Model"],
        **kwargs
    ):
        res = cls(**kwargs)
        for d in dicts:
            res._entries.update(d._entries)
        # === END FOR d ===

        # No need of cleaning caches
        return res
    # === END ===

    @functools.lru_cache(maxsize = 10240)
    def tokenize(self, req: str) -> typing.FrozenSet[typing.Tuple[Entry]]:
        def match_single_prefix(
            req: str,
            matched_obj: pygtrie.Trie._Step,
        ) -> typing.Iterable[typing.Iterator[Entry]]:
            prefix = matched_obj.key
            entries = matched_obj.value
            remainder = req[len(prefix):]

            if not remainder: # if you get to the end
                return ((entry, ) for entry in entries)
            else:
                return (
                    (entry, ) + subsequents
                    for entry, subsequents
                    in itertools.product(entries, self.tokenize(remainder)) 
                        # RECURSION
                )
            # === END IF ===
        # === END ===

        return frozenset(
            itertools.chain.from_iterable(
                match_single_prefix(req, word_candidate)
                for word_candidate
                in self._entries.prefixes(req)
            )
        )
    # === END ===

    yaml_tag = "!pymor-dict"

    @classmethod
    def to_yaml(
        cls, 
        representer, 
        node: "Model"
    ) -> yaml.nodes.MappingNode:
        return representer.represent_mapping(
            tag = cls.yaml_tag,
            mapping = {
                "version": 0,
                "content": list(node)
            }
        )
    # === END ===

    @classmethod
    def from_yaml(
        cls, 
        constructor: yaml.constructor.Constructor, 
        node: yaml.nodes.MappingNode
    ) -> "Model":
        dict_actual = yaml.comments.CommentedMap()
        constructor.construct_mapping(node, dict_actual, deep = True)
        
        ver = dict_actual["version"]
        res = cls()

        if True: # switch according to the version
            res.batchadd(dict_actual["content"])

        return res
    # === END ===
# === END CLASS ===

def load_model_dir(
    model_dir: typing.Union[str, pathlib.Path],
    name: typing.Optional[str] = None
) -> Model:
    if isinstance(model_dir, pathlib.Path):
        model_dir_path = model_dir
    elif isinstance(model_dir, str) or isinstance(model_dir, pathlib.PurePath):
        model_dir_path = pathlib.Path(model_dir)
    else:
        raise TypeError("""\
The model_dir argument of the loader (given as {obj}) must be of either type str or type pathlib.Path.
""".format(
            obj = repr(model_dir)
        )
    )
    # === END IF ===

    module_name = name if name else model_dir_path.name
    module_spec = imputil.spec_from_file_location(
        name = "mod" + module_name,
        location = model_dir_path / "mod.py"
    )
    module = imputil.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    cls_extdict = module.ExtModel

    yaml_engine = yaml.YAML()
    yaml_engine.register_class(Entry)
    yaml_engine.register_class(cls_extdict)

    return  cls_extdict.union(
        *map(
            yaml_engine.load,
            itertools.chain(
                model_dir_path.glob("**/*.dict.yaml"),
                model_dir_path.glob("**/*.dict.yml")
            )
        ),
        name = module_name,
        source_dir = model_dir_path,
        ext_src = "NotImplemented"
    )
# === END ===