import typing
import sys
import click
import ruamel.yaml as yaml

from . import obj
from . import repl
# ======
# Initialization
# ======
yaml_engine = yaml.YAML()
yaml_engine.register_class(obj.Entry)
yaml_engine.register_class(obj.Model)

# ======
# Commands
# ======
@click.group()
def cmd_main(): pass

@cmd_main.command("repl")
@click.option(
    "--model", "-m", "model_path",
    type = click.Path(
        exists = True,
        file_okay = False,
        dir_okay = True
    )
)
def cmd_repl(model_path: click.Path):
    state = repl.State(
        model = obj.load_model_dir(
            model_path
        )    
    )

    sys.exit(repl.main(state))
# === END ===

if __name__ == "__main__":
    cmd_main.__call__()