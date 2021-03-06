#!/usr/bin/env python
import os
import sys
from argparse import ArgumentParser, ArgumentTypeError


def valid_file(fname):
    if not os.path.isfile(fname):
        raise ArgumentTypeError("File was not found: {}".format(fname))
    return fname


def runExec(executable, args):
    os.execvp(executable, [executable] + args)


def runGui(args):
    runExec("python", ["-m", "ert_gui.gert_main"] + [args.config])


def runCli(args):
    runExec("python", ["-m", "ert_gui.cli"] +
            [args.config, args.mode, args.target_case])


def validate_cli_args(parser, args):
    if args.mode == "ensemble_smoother" and args.target_case == "default":
        msg = "Target file system and source file system can not be the same. "\
              "They were both: <default>. Please set using --target-case on "\
              "the command line."
        parser.error(msg)


def ert_parser():
    parser = ArgumentParser(description="ERT - Ensemble Reservoir Tool")

    subparsers = parser.add_subparsers(
        title="Available user entries",
        description='ERT can be accessed through a GUI or CLI interface. Include '
                    'one of the following arguments to change between the '
                    'interfaces. Note that different entry points may require '
                    'different additional arguments. See the help section for '
                    'each interface for more details.',
        help="Available entry points",
        dest="interface")

    gui_parser = subparsers.add_parser('gui',
                                       help='Graphical User Interface - opens up an independent window for '
                                       'the user to interact with ERT.',
                                       description='Graphical User Interface')
    gui_parser.add_argument('config', type=valid_file,
                            help="Ert configuration file")
    gui_parser.set_defaults(func=runGui)

    cli_parser = subparsers.add_parser('cli',
                                       help='Command Line Interface - provides a user interface in the terminal.',
                                       description="Command Line Interface")
    cli_parser.add_argument('config', type=valid_file,
                            help="Ert configuration file")
    cli_parser.add_argument("--mode", type=str, required=True,
                            choices=["test_run", "ensemble_experiment",
                                     "ensemble_smoother"],
                            help="The available modes")
    cli_parser.add_argument("--target-case", type=str, default="default",
                            help="The target filesystem to store results")
    cli_parser.set_defaults(func=runCli)
    return parser


def main():
    parser = ert_parser()
    args = parser.parse_args(sys.argv[1:])

    if args.interface == "cli":
        validate_cli_args(parser, args)

    args.func(args)
