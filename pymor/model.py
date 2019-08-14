import itertools
import typing

import pathlib
import importlib.util as imputil
import ruamel.yaml as yaml

from . import obj

def load_dir(
    model_dir: typing.Union[str, pathlib.Path],
    name: typing.Optional[str] = None
) -> obj.Dictionary:
    if isinstance(model_dir, pathlib.Path):
        pass
    elif isinstance(model_dir, str) or isinstance(model_dir, pathlib.PurePath):
        model_dir_path = pathlib.Path(model_dir)
    else:
        raise TypeError
    # === END IF ===
    module_name = name if name else model_dir_path.name

    module_spec = imputil.spec_from_file_location(
        name = "mod" + module_name,
        location = model_dir_path / "mod.py"
    )
    module = imputil.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    cls_extdict = module.ExtDictionary

    yaml_engine = yaml.YAML()
    yaml_engine.register_class(obj.Entry)
    yaml_engine.register_class(cls_extdict)

    return  cls_extdict.union(
        *map(
            yaml_engine.load,
            itertools.chain(
                model_dir_path.glob("**/*.dict.yaml"),
                model_dir_path.glob("**/*.dict.yml")
            )
        ),
        name = module_name
    )
# === END ===

if __name__ == "__main__":
    dic = load_dir("./smod/")
    print(dic)
    print(list(dic))