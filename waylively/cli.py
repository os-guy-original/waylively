import sys


USAGE = "Usage: waylively [--manager] | --daemon | --engine PATH | --screenshot HTML OUTPUT"


def _set_argv(argv):
    sys.argv = [sys.argv[0], *argv]


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        from waylively.ui.app import main as manager_main
        return manager_main()

    command, *rest = args

    if command in {"--manager", "manager"}:
        _set_argv(rest)
        from waylively.ui.app import main as manager_main
        return manager_main()

    if command in {"--daemon", "daemon"}:
        _set_argv(rest)
        from waylively.daemon.service import main as daemon_main
        return daemon_main()

    if command in {"--engine", "engine"}:
        _set_argv(rest)
        from waylively.engine.renderer import main as engine_main
        return engine_main()

    if command in {"--screenshot", "screenshot"}:
        _set_argv(rest)
        from waylively.screenshot import main as screenshot_main
        return screenshot_main()

    if command in {"-h", "--help", "help"}:
        print(USAGE)
        return 0

    print(USAGE, file=sys.stderr)
    return 1