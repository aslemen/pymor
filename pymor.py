import attr
import typing

import string
import collections
import pygtrie

import itertools
import functools

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
# === END CLASS ===

class Dictionary:
    def __init__(self, name: str, entries: typing.Iterable[Entry] = ()):
        self.name = name
        self._entries = pygtrie.CharTrie()
        for item in entries:
            self.add(item)
        # === END FOR items ===
    # === END ===

    def __getitem__(self, key: str) -> typing.Iterator[Entry]:
        return iter(self._entries.get(key, iter()))
    # === END ===

    def __iter__(self) -> typing.Iterator[Entry]:
        return itertools.chain.from_iterable(
            self._entries.values()
        )
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
        for entry in entries: self._add(entry)
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

    @functools.lru_cache(maxsize = 10240)
    def match(self, req: str) -> typing.Tuple[typing.Deque[Entry]]:
        def match_single_prefix(
            req: str,
            matched_obj: pygtrie.Trie._Step,
        ) -> typing.Iterable[typing.Iterator[Entry]]:
            prefix = matched_obj.key
            remainder = req[len(prefix):]
            entries = matched_obj.value

            if not remainder: # if you get to the end
                return (collections.deque((e, )) for entry in entries)
            else:
                def merge_product(
                    entry: Entry,
                    subsequents: typing.Deque[Entry]
                )-> typing.Deque[Entry]:
                    #print(subsequents)
                    deque_new = subsequents.copy()
                    deque_new.appendleft(entry)

                    return deque_new
                # === END ===

                return (
                    merge_product(entry, subsequents)
                    for entry, subsequents
                    in itertools.product(entries, self.match(remainder))
                )
            # === END IF ===
        # === END ===

        return itertools.chain.from_iterable(
            match_single_prefix(req, m)
            for m in self._entries.prefixes(req)
        )
    # === END ===
# === END CLASS ===

entries = [
    Entry(phon = "ar"),
    Entry(phon = "aru"),
    Entry(phon = "i"),
    Entry(phon = "ta", sem = "past"),
    Entry(phon = "ta", sem = "field")
]

d = Dictionary(name = "test")

for e in entries:
    d.add(e)

def populate(entry: Entry) -> typing.Set[Entry]:
    if entry.phon == "ar":
        return {entry, attr.evolve(entry, sem = "exist")}
    else:
        return {entry}
print(d._entries)

d.modify(populate)

print(d._entries)

d.delete(Entry(phon = "ar"))

print(d._entries)

for res in d.match("aruita"):
    print(list(res))