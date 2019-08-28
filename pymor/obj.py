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
    """
        Represents a lexical entry.

        Comparable, frozen and hashable.
    
        Attributes
        ----------
        phon : str
            The phonological form.
        feat : frozenset of (str, any), optional
            The feature bundle.
            Defaults to an empty `frozenset`.
        sem : str, optional
            The English translation. 
            Defaults to an empty string.
        gloss : str, optional
            The gloss for lemmatization. 
            Defaults to an empty string.

        Notes
        -----
        Instance cannot go through changes
        unless you make a new instance and setting up the parameters again.
        The `attr.evolve` method (in the `attrs` package) might be helpful.
        >>> import attr
        ... item = Entry(phon = "ice", sem = "solid water")
        ... attr.evolve(item, phon = "iced", sem = "being made icy")
        {iced:being made icy}

        To get a `dict` representation, 
        use the `attr.asdict` method in `attrs`.
    """

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
    ) -> yaml.nodes.MappingNode:
        """
        Provides a YAML serialization instruction.
        Made for `ruamel.yaml`.

        Examples
        --------
        >>> import ruamel.yaml as yaml
        ... yaml_engine = yaml.YAML()
        ... yaml_engine.register_class(Entry)
        ... item = Entry(
        ...     phon = "ices",
        ...     feat = frozenset([("scat", "NP")]),
        ...     sem = "iced water",
        ...     gloss = "ice.PL"
        ... )
        ... yaml_engine.dump(item)
        !e
        phon: ices
        feat:
          scat: NP
        sem: iced water
        gloss: ice.PL

        """
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
        """
        Provides a YAML deserialization instruction.
        Made for `ruamel.yaml`.

        Examples
        --------
        >>> import ruamel.yaml as yaml
        ... yaml_engine = yaml.YAML()
        ... yaml_engine.register_class(Entry)
        ... yaml_engine.load('''
        ... !e
        ... phon: ices
        ... sem: solid water
        ... ''')
        {ices:solid water}
        
        """
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
    """
    Represents a basic langauge model,
    which consists of 
    a list of lexical entries (of type `ENTRY`),
    instructions to populate their allomorphs,
    and a parser to analyze words. 
    
    A model is formed by registering lexical items,
    a process which is sometimes accompanied 
    with gerenating their allomorphs by given morphological rules.
    This is why we have 2*2 functions --- `add_raw`, `add` and
    their batch variants.
    The `add_raw` method adds a lexical item without any modification
    while `add` adds a bunch of items resulting from 
    the `populate` method, customized by users, applied to the input item.
    The registered lexical entries are stored in a private 
    trie which can be accessed via indexer,
    in which indices are the phonological forms of the entries:

    >>> m = Model(name = "test")
    ... m.add(Entry(phon = "abc", sem = "1"))
    ... m.add(Entry(phon = "abc", sem = "2"))
    ... lexs = m["abc"]
    ... "; ".join(lexs)
    {abc:1}; {abc:2}

    Note that since it is not rare to have homophones, the indexer will
    returns an iterator of `Entry`s rather than a single one.

    Parsing a word can thus be done with a set of registered lexical items
    along with a tokenizer `tokenize`
    and a lexical grammar specified by the (overwritable) `parse` method.

    As already noted,
    users can customize this class by inheriting it and overriting 
    the `populate` and `parse` methods; 
    in fact, models of particular languages are supposed to be thus made.

    Models are either specified dynamically or stored in files.
    For the details of the latter, refer to the `load_model_dir` method.

    Arguments
    ---------
    name : str, optional
        The name of the model. Defaults to "<UNTITLED>".
    source_dir : str, optional
        The source location of the model in the file system.
    ext_src : str, optional.
        The source code of the model. Yet to be implemented.
    """

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
        """
        Clear methods' LRU caches of the instance.
        """
        self.tokenize.cache_clear()
    # === END ===

    @staticmethod
    def populate(entry: Entry) -> typing.Iterator[Entry]:
        yield entry
    # ======

    def _add(self, entry: Entry) -> typing.NoReturn:
        phon = entry.phon

        if phon not in self._entries:
            self._entries[phon] = set((entry, ))
        else:
            self._entries[phon].add(entry)
        # === END IF ===
    # === END ===

    def add_raw(self, entry: Entry) -> typing.NoReturn:
        self._add(entry)
        self.clear_caches()
    # === END ===

    def add_raw_batch(
        self,
        entries: typing.Iterable[Entry]
    ) -> typing.NoReturn:
        for entry in entries:
            self._add(entry)
        # === END FOR entry ===
        
        self.clear_caches()
    # === END ===

    def add(self, entry: Entry) -> typing.NoReturn:
        """
        Warings
        ------
        Not supposed to be overrided.
        """
        for gen_entry in self.populate(entry):
            self._add(gen_entry)
        # === END ===

        self.clear_caches()
    # === END ===

    def add_batch(self, entries: typing.Iterable[Entry]) -> typing.NoReturn:
        """
        Warnings
        --------
        Not supposed to be overrided.
        """
        
        for gen_entry in itertools.chain.from_iterable(
            map(self.populate, entries)
        ): 
            self._add(gen_entry)
        # === END FOR gen_entry ===

        self.clear_caches()
    # === END ===

    def delete(self, entry: Entry) -> typing.NoReturn:
        """
        Delete a lexical entry.
        Nothing happens when it does not registered.

        Notes
        -----
        Allomorphs generated through registeration will not deleted
        along with the given entry.

        Warnings
        --------
        Not supposed to be overrided.
        """
        
        phon = entry.phon
        
        if phon in self._entries:
            self._entries[phon].discard(entry)
            self.clear_caches()
        # === END IF ===
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
        
        _ = dict_actual["version"]
        res = cls()

        if True: # switch according to the version
            res.add_batch(dict_actual["content"])

        return res
    # === END ===
# === END CLASS ===

def load_model_dir(
    model_dir: typing.Union[str, pathlib.Path],
    name: typing.Optional[str] = None
) -> Model:
    """
    Load a model (of type `Model`) from a directory.

    Arguments
    ---------
    model_dir : str or pathlib.Path
        The path to the directory.
        The directory consists of the following files:
        `mod.py`
            stores the custom class, 
            which must be named `ExtModel`
            and made to inherit the `Model` class.
        `**/*.dict.yaml` or `**/*.dict.yml`
            stores lexical entries.
    """
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

    
    return cls_extdict.union(
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