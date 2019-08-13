import attr
import typing

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
class Dictionary:
    name = attr.ib(
        repr = True,
        init = True,
        default = "<UNTITLED>",
        kw_only = True,
        type = str,
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
        self.match.cache_clear()
    # === END ===

    def batchadd(self, entries: typing.Iterable[Entry]) -> typing.NoReturn:
        for entry in entries: 
            self._add(entry)
        self.match.cache_clear()
    # === END ===

    def delete(self, entry: Entry) -> typing.NoReturn:
        phon = entry.phon
        
        if phon in self._entries:
            self._entries[phon].discard(entry)
            self.match.cache_clear()
        # === END IF ===
    # === END ===
    
    def modify(
        self,
        func: typing.Mapping[Entry, typing.Set[Entry]]
    ) -> typing.NoReturn:
        old_dict = self._entries
        self._entries = pygtrie.CharTrie()
        self.match.cache_clear()

        for new_entry in itertools.chain.from_iterable(
            func(old_entry)
            for old_entry in itertools.chain.from_iterable(
                old_dict.values()
            )
        ):
            self.add(new_entry)
        # === END FOR entry ====
    # === END ===

    def populate(
        self, 
        func: typing.Mapping[Entry, typing.Set[Entry]]
    ) -> "Dictionary":
        return Dictionary(
            name = self.name,
            entries = map(func, iter(self))
        )
    # === END ===

    def merge(
        self,
        other: "Dictionary"
    ):
        self._entries.update(other._entries)
        self.match.cache_clear()
    # === END ===

    @classmethod
    def union(
        cls,
        *dicts: typing.List["Dictionary"],
        name: str = "<UNTITLED>"
    ):
        res = cls(name = name)
        for d in dicts:
            res._entries.update(d._entries)
        # === END FOR d ===

        # No need of cleaning caches
        return res
    # === END ===

    @functools.lru_cache(maxsize = 10240)
    def match(self, req: str) -> typing.FrozenSet[typing.Tuple[Entry]]:
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
                    in itertools.product(entries, self.match(remainder))
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
        node: "Dictionary"
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
    ) -> "Dictionary":
        dict_actual = yaml.comments.CommentedMap()
        constructor.construct_mapping(node, dict_actual, deep = True)

        ver = dict_actual["version"]
        res = cls()

        if True: # switch according to the version
            res.batchadd(dict_actual["content"])

        return res
    # === END ===
# === END CLASS ===