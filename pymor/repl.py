import typing
import attr

import itertools

import os
import pathlib
import ruamel.yaml as yaml

import prompt_toolkit as pt

import obj


# ======
# Initialization
# ======
# ------
# The Yaml Engine
# ------
yaml_engine = yaml.YAML()
yaml_engine.register_class(obj.Dictionary)
yaml_engine.register_class(obj.Entry)

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

    dictionary = attr.ib(
        factory = lambda: obj.Dictionary(name = "<SESSION>"),
        repr = False,
        type = obj.Dictionary
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

    def give_info(self, txt: str) -> typing.NoReturn:
        self.write_formatted(
            ("class:info", "INFO: "),
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
        state.give_info("analyzing word #{num}".format(num = num))
        
        word_candidates = state.dictionary.match(word)

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
        state.write_formatted(
            ("class:info", "Current Working Directory: ")
            ,
            ("", str(pathlib.Path.cwd()))
        )
    elif command == ":load":
        try:
            for fp in map(pathlib.Path, command_args):
                with open(fp, "r") as f:
                    path_full = fp.absolute()
                    filename = fp.name

                    state.give_info(
                        "opened the dictionary {path}".format(
                            path = path_full
                        )
                    )

                    new_dict = yaml_engine.load(f)

                    state.give_info(
                        "fetched {num} entries(s) from {name}".format(
                            num = len(new_dict),
                            name = filename
                        )
                    )

                    state.dictionary.merge(new_dict)

                    state.give_info(
                        "successfully incorporated entries from {fn}".format(
                            fn = filename
                        )
                    )
                # === END WITH f ===
            # === END FOR fp ===
        except FileNotFoundError as not_found:
            state.give_error("invalid file name: " + not_found.filename)
        except Exception as e:
            raise e
        # === END TRY ===
    elif command == ":dict":
        dic = state.dictionary

        if dic._entries:
            pt.print_formatted_text(
                "\n".join(map(repr, state.dictionary))
            )
        else:
            state.session.prompt("EMPTY")
        # === END IF ===
    elif command == ":match":
        cmd_batch_analyze(command_args, state)
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
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        else:
            route(command_raw, state)
# === END ===

if __name__ == "__main__":
    main()