import typing
import sys
import click
import ruamel.yaml as yaml

from . import repl
from . import obj

# ======
# Initialization
# ======
yaml_engine = yaml.YAML()
yaml_engine.register_class(obj.Entry)
yaml_engine.register_class(obj.Dictionary)


# ======
# Commands
# ======
@click.group()
def cmd_main(): pass

@cmd_main.command("repl")
@click.option(
    "--dict", "-d", "files",
    multiple = True,
    type = click.File()
)
def cmd_repl(files: typing.Iterable[click.File]):
    dicts = map(yaml_engine.load, files)

    state = repl.State(
        dictionary = obj.Dictionary.union(*dicts)
    )


    sys.exit(repl.main(state))
# === END ===


if __name__ == "__main__":
    cmd_main.__call__()