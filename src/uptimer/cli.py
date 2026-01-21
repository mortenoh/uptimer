"""CLI for uptimer."""

import json
from datetime import datetime, timezone
from typing import Annotated

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from uptimer import __version__
from uptimer.client import AuthenticationError, NotFoundError, UptimerClient, UptimerClientError
from uptimer.schemas import CheckConfig, MonitorCreate

app = typer.Typer(
    name="uptimer",
    help="Service uptime monitoring CLI",
    no_args_is_help=True,
)
console = Console()

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


def _get_client() -> UptimerClient:
    """Get configured API client."""
    from uptimer.settings import get_settings

    settings = get_settings()
    return UptimerClient(
        base_url=settings.api_url,
        username=settings.username,
        password=settings.password,
    )


def _handle_client_error(e: UptimerClientError) -> None:
    """Handle client errors with appropriate messages."""
    if isinstance(e, AuthenticationError):
        rprint("[red]Authentication failed. Check your credentials.[/red]")
    elif isinstance(e, NotFoundError):
        rprint("[red]Not found.[/red]")
    else:
        rprint(f"[red]Error: {e}[/red]")
    raise typer.Exit(1)


def _format_time_ago(dt: datetime) -> str:
    """Format datetime as relative time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


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


@app.command("list")
def list_monitors(
    tag: Annotated[str | None, typer.Option("--tag", "-t", help="Filter by tag")] = None,
) -> None:
    """List all monitors."""
    try:
        client = _get_client()
        monitors = client.list_monitors(tag=tag)
    except UptimerClientError as e:
        _handle_client_error(e)
        return

    if _json_output:
        print(json.dumps([m.model_dump(mode="json") for m in monitors], indent=2))
        return

    if not monitors:
        rprint("[dim]No monitors found.[/dim]")
        return

    table = Table()
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("URL")
    table.add_column("Status")
    table.add_column("Last Check")

    for m in monitors:
        status_style = {"up": "green", "degraded": "yellow", "down": "red"}.get(m.last_status or "", "dim")
        status_text = f"[{status_style}]{m.last_status or '-'}[/{status_style}]"
        last_check = _format_time_ago(m.last_check) if m.last_check else "-"
        table.add_row(m.id[:8], m.name, m.url, status_text, last_check)

    console.print(table)


@app.command("get")
def get_monitor(
    monitor_id: Annotated[str, typer.Argument(help="Monitor ID")],
) -> None:
    """Get monitor details."""
    try:
        client = _get_client()
        monitor = client.get_monitor(monitor_id)
    except UptimerClientError as e:
        _handle_client_error(e)
        return

    if _json_output:
        print(json.dumps(monitor.model_dump(mode="json"), indent=2))
        return

    status_style = {"up": "green", "degraded": "yellow", "down": "red"}.get(monitor.last_status or "", "dim")

    rprint(f"[bold]{monitor.name}[/bold]")
    rprint(f"  [dim]ID:[/dim] {monitor.id}")
    rprint(f"  [dim]URL:[/dim] {monitor.url}")
    rprint(f"  [dim]Status:[/dim] [{status_style}]{monitor.last_status or '-'}[/{status_style}]")
    rprint(f"  [dim]Enabled:[/dim] {'Yes' if monitor.enabled else 'No'}")
    rprint(f"  [dim]Interval:[/dim] {monitor.interval}s")
    if monitor.schedule:
        rprint(f"  [dim]Schedule:[/dim] {monitor.schedule}")
    if monitor.tags:
        rprint(f"  [dim]Tags:[/dim] {', '.join(monitor.tags)}")
    rprint("  [dim]Checks:[/dim]")
    for check in monitor.checks:
        rprint(f"    - {check.type}")
    if monitor.last_check:
        rprint(f"  [dim]Last Check:[/dim] {_format_time_ago(monitor.last_check)}")
    rprint(f"  [dim]Created:[/dim] {monitor.created_at.strftime('%Y-%m-%d %H:%M:%S')}")


@app.command("add")
def add_monitor(
    name: Annotated[str, typer.Argument(help="Monitor name")],
    url: Annotated[str, typer.Argument(help="URL to monitor")],
    check: Annotated[list[str] | None, typer.Option("--check", "-c", help="Checker type (can be repeated)")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", "-t", help="Tag (can be repeated)")] = None,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Check interval in seconds")] = 30,
    schedule: Annotated[str | None, typer.Option("--schedule", "-s", help="Cron schedule expression")] = None,
) -> None:
    """Create a new monitor."""
    checks = [CheckConfig(type=c) for c in check] if check else [CheckConfig(type="http")]
    tags = list(tag) if tag else []

    data = MonitorCreate(
        name=name,
        url=url,
        checks=checks,
        tags=tags,
        interval=interval,
        schedule=schedule,
    )

    try:
        client = _get_client()
        monitor = client.create_monitor(data)
    except UptimerClientError as e:
        _handle_client_error(e)
        return

    if _json_output:
        print(json.dumps(monitor.model_dump(mode="json"), indent=2))
        return

    rprint(f"[green]Created monitor:[/green] {monitor.name} ({monitor.id})")


@app.command("delete")
def delete_monitor(
    monitor_id: Annotated[str, typer.Argument(help="Monitor ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a monitor."""
    if not force:
        confirm = typer.confirm(f"Delete monitor {monitor_id}?")
        if not confirm:
            raise typer.Abort()

    try:
        client = _get_client()
        client.delete_monitor(monitor_id)
    except UptimerClientError as e:
        _handle_client_error(e)
        return

    if not _json_output:
        rprint(f"[green]Deleted monitor {monitor_id}[/green]")


@app.command("check")
def run_check(
    monitor_id: Annotated[str, typer.Argument(help="Monitor ID")],
) -> None:
    """Run a check for a monitor."""
    try:
        client = _get_client()
        result = client.run_check(monitor_id)
    except UptimerClientError as e:
        _handle_client_error(e)
        return

    if _json_output:
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        return

    status_style = {"up": "green", "degraded": "yellow", "down": "red"}.get(result.status, "dim")
    rprint(f"[{status_style}]{result.status.upper()}[/{status_style}] {result.message} ({result.elapsed_ms:.0f}ms)")


@app.command("check-all")
def check_all(
    tag: Annotated[str | None, typer.Option("--tag", "-t", help="Filter by tag")] = None,
) -> None:
    """Run checks for all monitors."""
    try:
        client = _get_client()
        results = client.run_all_checks(tag=tag)
    except UptimerClientError as e:
        _handle_client_error(e)
        return

    if _json_output:
        print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
        return

    if not results:
        rprint("[dim]No monitors to check.[/dim]")
        return

    for result in results:
        status_style = {"up": "green", "degraded": "yellow", "down": "red"}.get(result.status, "dim")
        rprint(
            f"[{status_style}]{result.status.upper()}[/{status_style}] "
            f"[dim]{result.monitor_id[:8]}[/dim] {result.message} ({result.elapsed_ms:.0f}ms)"
        )


@app.command("results")
def get_results(
    monitor_id: Annotated[str, typer.Argument(help="Monitor ID")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of results")] = 10,
) -> None:
    """Get check history for a monitor."""
    try:
        client = _get_client()
        results = client.get_results(monitor_id, limit=limit)
    except UptimerClientError as e:
        _handle_client_error(e)
        return

    if _json_output:
        print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
        return

    if not results:
        rprint("[dim]No results found.[/dim]")
        return

    table = Table()
    table.add_column("Time")
    table.add_column("Status")
    table.add_column("Message")
    table.add_column("Duration")

    for r in results:
        status_style = {"up": "green", "degraded": "yellow", "down": "red"}.get(r.status, "dim")
        status_text = f"[{status_style}]{r.status}[/{status_style}]"
        time_str = _format_time_ago(r.checked_at)
        table.add_row(time_str, status_text, r.message[:50], f"{r.elapsed_ms:.0f}ms")

    console.print(table)


@app.command("tags")
def list_tags() -> None:
    """List all tags."""
    try:
        client = _get_client()
        tags = client.list_tags()
    except UptimerClientError as e:
        _handle_client_error(e)
        return

    if _json_output:
        print(json.dumps(tags, indent=2))
        return

    if not tags:
        rprint("[dim]No tags found.[/dim]")
        return

    for tag in tags:
        rprint(f"  [cyan]{tag}[/cyan]")


@app.command()
def checkers() -> None:
    """List available checkers."""
    from uptimer.checkers import get_checker, list_checkers

    checker_list = list_checkers()

    if _json_output:
        data: list[dict[str, str]] = []
        for name in checker_list:
            checker_class = get_checker(name)
            data.append({"name": name, "description": checker_class.description})
        print(json.dumps(data, indent=2))
        return

    for name in checker_list:
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
