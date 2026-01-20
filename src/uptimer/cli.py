"""CLI for uptimer."""

import typer
from rich import print as rprint
from rich.console import Console

from uptimer import __version__
from uptimer.logging import configure_logging

app = typer.Typer(
    name="uptimer",
    help="Service uptime monitoring CLI",
    no_args_is_help=True,
)
console = Console()

# Global state for JSON output mode
_json_output = False


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        rprint(f"uptimer [cyan]{__version__}[/cyan]")
        raise typer.Exit()


def json_callback(value: bool) -> None:
    """Enable JSON output mode."""
    global _json_output  # noqa: PLW0603
    _json_output = value
    if value:
        configure_logging(json_output=True)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        callback=json_callback,
        is_eager=True,
        help="Output as JSON.",
    ),
) -> None:
    """Uptimer - Service uptime monitoring CLI."""
    pass


@app.command()
def check(
    url: str = typer.Argument(..., help="URL to check"),
    checker: str = typer.Option("http", "--checker", "-c", help="Checker to use"),
    username: str | None = typer.Option(None, "--username", "-u", help="Username for auth"),
    password: str | None = typer.Option(None, "--password", "-p", help="Password for auth"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed request info"),
) -> None:
    """Check if a URL is up."""
    from uptimer.checkers import Status, get_checker
    from uptimer.logging import get_logger

    # Get checker and run
    checker_class = get_checker(checker)

    # Build kwargs for checker based on what it supports
    kwargs: dict[str, object] = {}
    if username is not None:
        kwargs["username"] = username
    if password is not None:
        kwargs["password"] = password

    checker_instance = checker_class(**kwargs)
    result = checker_instance.check(url, verbose=verbose)

    if _json_output:
        # JSON output via structlog
        log = get_logger("uptimer.check")
        log.info(
            "check_complete",
            status=result.status.value,
            url=result.url,
            message=result.message,
            elapsed_ms=round(result.elapsed_ms, 2),
            **result.details,
        )
    else:
        # Rich console output
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

            # DHIS2 specific
            if "version" in details:
                rprint(f"  [dim]Version:[/dim] {details['version']}")
            if "system_name" in details:
                rprint(f"  [dim]System:[/dim] {details['system_name']}")
            if "server_date" in details:
                rprint(f"  [dim]Server Date:[/dim] {details['server_date']}")

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
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
) -> None:
    """Start the web UI server."""
    import uvicorn

    from uptimer.settings import get_settings

    settings = get_settings()
    actual_host = host or settings.host
    actual_port = port or settings.port

    rprint(f"Starting server at [cyan]http://{actual_host}:{actual_port}[/cyan]")
    rprint(f"Login with [cyan]{settings.username}[/cyan] / [dim]****[/dim]")

    uvicorn.run(
        "uptimer.web:create_app",
        host=actual_host,
        port=actual_port,
        reload=reload,
        factory=True,
    )


@app.command()
def version() -> None:
    """Show version information."""
    rprint(f"uptimer [cyan]{__version__}[/cyan]")


@app.command()
def init() -> None:
    """Initialize configuration file."""
    from pathlib import Path

    config_file = Path("config.yaml")
    example_file = Path("config.example.yaml")

    if config_file.exists():
        rprint("[yellow]config.yaml already exists[/yellow]")
        return

    if not example_file.exists():
        rprint("[red]config.example.yaml not found[/red]")
        raise typer.Exit(1)

    config_file.write_text(example_file.read_text())
    rprint("[green]Created config.yaml from config.example.yaml[/green]")
    rprint("Edit config.yaml to customize your settings.")
