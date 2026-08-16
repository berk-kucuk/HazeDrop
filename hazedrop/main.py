import sys


def main():
    from hazedrop.core.settings import load_settings
    from hazedrop.i18n import set_language
    set_language(load_settings().language)

    args = sys.argv[1:]
    cli_triggers = {"send", "receive", "--cli", "-h", "--help", "--version"}

    if any(a in cli_triggers for a in args) or (args and not args[0].startswith("-")):
        from hazedrop.cli.app import main as cli_main
        cli_main(standalone_mode=True)
    else:
        from hazedrop.gui.main_window import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()
