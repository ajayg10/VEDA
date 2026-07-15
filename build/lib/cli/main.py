import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import httpx
from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table
from rich         import box

from shared.models import (
    RunRequest, OrchestrationResult,
    ExecutionPlan, StepStatus,
)

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")
console = Console()

api_key = os.getenv("VEDA_API_KEY", "")
headers = {"X-API-Key": api_key} if api_key else {}
client = httpx.AsyncClient(
        base_url="http://localhost", 
        headers=headers, 
        timeout=120)

def render_plan(plan: ExecutionPlan) -> None:
    complexity_color = {"low": "green", "medium": "yellow", "high": "red"}.get(
        plan.estimated_complexity, "white"
    )
    badge = (
        "[bold red]⚠  YES — confirm before running[/bold red]"
        if plan.requires_confirmation
        else "[green]✓  Safe to execute[/green]"
    )
    console.print(Panel(
        f"[bold cyan]Goal:[/bold cyan] {plan.goal}\n\n"
        f"[bold]Reasoning:[/bold] {plan.reasoning}\n\n"
        f"Complexity: [{complexity_color}]{plan.estimated_complexity.upper()}[/{complexity_color}]"
        f"   Confirmation required: {badge}",
        title="[bold green]✦ VEDA Execution Plan[/bold green]",
        border_style="green",
    ))

    tbl = Table(box=box.ROUNDED, header_style="bold magenta", show_lines=True)
    tbl.add_column("#",           style="dim",      width=3)
    tbl.add_column("Tool",        style="cyan",      width=16)
    tbl.add_column("Description", style="white",     min_width=28)
    tbl.add_column("Depends on",  style="yellow",    width=12)
    tbl.add_column("Rationale",   style="dim white", min_width=20)
    for step in plan.steps:
        deps = ", ".join(str(d) for d in step.depends_on) if step.depends_on else "—"
        tbl.add_row(str(step.step_id), step.tool.value, step.description, deps, step.rationale)
    console.print(tbl)


def render_memories(memories: list) -> None:
    if not memories:
        return
    tbl = Table(box=box.SIMPLE, header_style="bold dim", show_lines=False)
    tbl.add_column("Score", style="dim", width=6)
    tbl.add_column("Past goal",           min_width=40)
    tbl.add_column("Status",              width=10)
    for m in memories:
        status = "[green]✓[/green]" if m.succeeded else "[red]✗[/red]"
        tbl.add_row(f"{m.score:.2f}", m.goal, status)
    console.print(Panel(tbl, title="[dim]✦ Memory — similar past goals[/dim]", border_style="dim"))


def render_results(result) -> None:
    overall_color = "green" if result.status == StepStatus.SUCCESS else "red"
    overall_label = "✦ COMPLETED" if result.status == StepStatus.SUCCESS else "✦ FAILED"

    tbl = Table(box=box.ROUNDED, header_style="bold magenta", show_lines=True)
    tbl.add_column("#",      style="dim",  width=3)
    tbl.add_column("Status", width=10)
    tbl.add_column("Output / Error", min_width=40)
    tbl.add_column("ms",     style="dim",  width=8)

    icons = {
        StepStatus.SUCCESS: "[green]✓  ok[/green]",
        StepStatus.FAILED:  "[red]✗  fail[/red]",
        StepStatus.SKIPPED: "[yellow]⊘  skip[/yellow]",
    }
    for r in result.step_results:
        content = r.output if r.status == StepStatus.SUCCESS else r.error
        preview = content[:200] + "…" if len(content) > 200 else content
        tbl.add_row(str(r.step_id), icons.get(r.status, "?"), preview, f"{r.duration_ms:.0f}")

    console.print(Panel(
        tbl,
        title=f"[bold {overall_color}]{overall_label} — {result.total_duration_ms:.0f}ms total[/bold {overall_color}]",
        border_style=overall_color,
    ))


async def check_services(client: httpx.AsyncClient) -> bool:
    """Ping all four services before starting the REPL."""
    services = {
        "orchestrator": f"{ORCHESTRATOR_URL}/health",
        "planner":      "http://localhost:8001/health",
        "memory":       "http://localhost:8002/health",
        "executor":     "http://localhost:8003/health",
    }
    all_up = True
    for name, url in services.items():
        try:
            r = await client.get(url, timeout=3)
            status = "[green]✓[/green]" if r.status_code == 200 else "[red]✗[/red]"
        except Exception:
            status = "[red]✗  unreachable[/red]"
            all_up = False
        console.print(f"  {status} {name}")
    return all_up


async def repl() -> None:
    console.print(Panel(
        "[bold green]VEDA[/bold green] — Virtual Execution & Decision Architecture\n"
        "[dim]Phase 4 · Distributed Microservices · type 'exit' to quit[/dim]",
        border_style="green",
    ))

    async with httpx.AsyncClient(timeout=60.0) as client:
        console.print("\n[dim]Checking services…[/dim]")
        all_up = await check_services(client)
        if not all_up:
            console.print(
                "\n[bold red]Some services are down.[/bold red] "
                "Start all four before running the CLI.\n"
            )
            return

        console.print()

        while True:
            try:
                console.print("\n[bold green]veda >[/bold green] ", end="")
                user_input = input().strip()
                
                if user_input.startswith("analyze "):

                    path = user_input.split(" ", 1)[1]
                    from core.project.scanner import ProjectScanner
                    scanner = ProjectScanner()
                    info = scanner.scan(path)
                    console.print(info)

                    continue

                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    console.print("[dim]Shutting down.[/dim]")
                    break

                # ── Mode A: get plan from orchestrator ─────────────────────
                with console.status("[bold green]Planning…[/bold green]", spinner="dots"):
                    resp = await client.post(
                        f"{ORCHESTRATOR_URL}/run",
                        json=RunRequest(goal=user_input).model_dump(),
                    )

                if resp.status_code != 200:
                    console.print(f"[red]Orchestrator error:[/red] {resp.text}")
                    continue

                orch = OrchestrationResult(**resp.json())
                render_memories(orch.memories)
                render_plan(orch.plan)

                # ── Confirmation ───────────────────────────────────────────
                if orch.plan.requires_confirmation:
                    console.print("\n[bold red]⚠  WARNING:[/bold red] Destructive operations detected.\n")
                console.print("[bold]Execute this plan?[/bold] [dim](yes / no)[/dim] ", end="")
                if input().strip().lower() not in ("yes", "y"):
                    console.print("[dim]Execution skipped.[/dim]")
                    continue

                # ── Mode B: execute the approved plan ──────────────────────
                with console.status("[bold green]Executing…[/bold green]", spinner="dots"):
                    resp = await client.post(
                        f"{ORCHESTRATOR_URL}/run",
                        json=RunRequest(
                            goal=user_input,
                            plan=orch.plan,
                            auto_execute=True,
                        ).model_dump(),
                    )

                if resp.status_code != 200:
                    console.print(f"[red]Execution error:[/red] {resp.text}")
                    continue

                orch2 = OrchestrationResult(**resp.json())
                render_results(orch2.result)
                console.print("[dim]✦ Stored to memory.[/dim]")

            except KeyboardInterrupt:
                console.print("\n[dim]Interrupted.[/dim]")
                break
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")


def main():
    asyncio.run(repl())


if __name__ == "__main__":
    main()