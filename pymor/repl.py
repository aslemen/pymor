import typing
import attr

import itertools

import os
import pathlib
import ruamel.yaml as yaml

import prompt_toolkit as pt

from . import obj

# ======
# Initialization
# ======

# ------
# Prompt Style
# ------
default_style = pt.styles.Style.from_dict(
    {
        "prompt": "#999999",
        "error": "#FF6666",
        "info": "#FFFF66"
    }
)

@attr.s(
    slots = True,
    cmp = False
)
class State:
    session = attr.ib(
        factory = lambda: pt.PromptSession(style = default_style),
        repr = False,
        type = pt.PromptSession
    )

    model = attr.ib(
        factory = lambda: obj.Model(name = "<SESSION>"),
        type = obj.Model
    )

    def readline(self) -> str:
        return self.session.prompt(
            [
                ("class:prompt", "[pymor]>> ")

            ]
        )
    # === END ===

    def write_formatted(
        self, 
        *contents: typing.List[typing.Tuple]
    ) -> typing.NoReturn:
        pt.print_formatted_text(
            pt.formatted_text.FormattedText(list(contents))
            ,
            style = self.session.style
        )
    # === END ===

    def give_info(
        self, 
        txt: str, 
        kind: str = "INFO"
    ) -> typing.NoReturn:
        self.write_formatted(
            ("class:info", kind + ": "),
            ("", txt),
        )
    # === END === 

    def give_error(self, txt: str) -> typing.NoReturn:
        self.write_formatted(
            ("class:error", "ERROR: "),
            ("", txt),
        )
    # === END ===
# === END CLASS ===

# ======
# Commands
# ======
def cmd_batch_analyze(words: typing.Iterable[str], state: State):
    for num, word in enumerate(words, 1):
        state.give_info(
            "analyzing word #{num}: {word}".format(
                num = num,
                word = word,
            )
        )
        
        word_candidates = state.model.match(word)

        if word_candidates:
            for candidate in word_candidates:
                pt.print_formatted_text(
                    "-".join(map(str, candidate))
                )
        else:
            state.give_info(
                "no matches for {word}".format(
                    word = word
                )
            )
        # === END FOR candidate ===
    # === END FOR word, num ===
# === END ===

def route(
    command_raw: str,
    state: State
) -> typing.NoReturn:
    command_token = command_raw.split()

    if not command_token: # NO INPUT
        return
    # === END IF ===

    command = command_token[0]
    command_args = command_token[1:]
    if command == ":pwd":
        state.give_info(
            str(pathlib.Path.cwd()),
            kind = "Current Working Directory"
        )
    elif command == ":reload":
        if len(command_args) != 1:
            state.give_error(
                "Exactly one argument is required"
            )
            return
        # === END IF ===

        try:
            path = pathlib.Path(command_args[0])
            
            state.give_info(
                "reached the model {path}".format(
                    path = path.absolute()
                )
            )

            state.model = obj.load_model_dir(path)

            state.give_info(
                "successfully incorporated entries from {fn}".format(
                    fn = path.name
                )
            )
        except FileNotFoundError as not_found:
            state.give_error("invalid file path: " + not_found.filename)
        except Exception as e:
            raise e
        # === END TRY ===
    elif command == ":model":
        model = state.model

        state.give_info(
            model.name,
            kind = "Model Name"
        )

        path_raw = model.source_dir
        
        if isinstance(path_raw, pathlib.Path):
            path = str(path_raw.absolute())
        else:
            path = str(path_raw)
        # === END IF ===

        state.give_info(
            path,
            kind = "Path to the Model"
        )

        state.give_info(
            (
                "\n" + "\n".join(map(repr, model))
                if model._entries
                else "empty"
            ),
            kind = "Dictionary"
        )
        # === END IF ===
    elif command == ":model-ext-src":
        state.give_info(
            state.model.ext_src,
            kind = "Source Code of the Model Extension"
        )
    elif command == ":match":
        cmd_batch_analyze(command_args, state)
    elif command in [":exit", ":quit"] :
        raise EOFError
    elif command.startswith(":"):
        state.give_error("invalid command")
    else: 
        cmd_batch_analyze(command_token, state)
# === END ===

# ======
# Routines
# ======
def main(state: State = State()):
    while True:
        try:
            command_raw = state.readline()
            route(command_raw, state)
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
    # === END WHILE ===            
# === END ===

if __name__ == "__main__":
    main()