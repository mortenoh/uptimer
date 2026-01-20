"""CLI for uptimer."""

import typer
from rich import print as rprint
from rich.console import Console

from uptimer import __version__

app = typer.Typer(
    name="uptimer",
    help="Service uptime monitoring CLI",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        rprint(f"uptimer [cyan]{__version__}[/cyan]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Uptimer - Service uptime monitoring CLI."""
    pass


@app.command()
def check(
    url: str = typer.Argument(..., help="URL to check"),
    checker: str = typer.Option("http", "--checker", "-c", help="Checker to use"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed request info"),
) -> None:
    """Check if a URL is up."""
    from uptimer.checkers import Status, get_checker

    # Get checker and run
    checker_class = get_checker(checker)
    checker_instance = checker_class()
    result = checker_instance.check(url, verbose=verbose)

    # Display status
    status_colors = {
        Status.UP: "green",
        Status.DEGRADED: "yellow",
        Status.DOWN: "red",
    }
    color = status_colors[result.status]
    rprint(f"[{color}]{result.status.name}[/{color}] {result.url} ({result.message})")

    # Verbose output
    if verbose:
        details = result.details

        # Show redirect chain if any
        if "redirects" in details:
            rprint("  [dim]Redirects:[/dim]")
            for r in details["redirects"]:
                rprint(f"    [dim]{r['status']}[/dim] -> {r['location']}")
            rprint(f"  [dim]Final URL:[/dim] {details.get('final_url', '')}")

        if result.elapsed_ms:
            rprint(f"  [dim]Time:[/dim] {result.elapsed_ms:.0f}ms")
        if "http_version" in details:
            rprint(f"  [dim]HTTP:[/dim] {details['http_version']}")
        if "server" in details:
            rprint(f"  [dim]Server:[/dim] {details['server']}")
        if "content_type" in details:
            rprint(f"  [dim]Content-Type:[/dim] {details['content_type']}")
        if "error" in details:
            rprint(f"  [dim]Error:[/dim] {details['error']}")

    if result.status == Status.DOWN:
        raise typer.Exit(1)


@app.command()
def checkers() -> None:
    """List available checkers."""
    from uptimer.checkers import get_checker, list_checkers

    for name in list_checkers():
        checker_class = get_checker(name)
        rprint(f"  [cyan]{name}[/cyan] - {checker_class.description}")


@app.command()
def version() -> None:
    """Show version information."""
    rprint(f"uptimer [cyan]{__version__}[/cyan]")
