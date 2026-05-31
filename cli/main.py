import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table
from rich         import box

from core.planner  import Planner
from core.executor import Executor
from shared.models import ExecutionPlan, ExecutionResult, StepStatus
from core.memory import MemoryManager
console = Console()


def render_plan(plan: ExecutionPlan) -> None:
    complexity_color = {"low": "green", "medium": "yellow", "high": "red"}.get(
        plan.estimated_complexity, "white"
    )
    confirmation_badge = (
        "[bold red]⚠  YES — confirm before running[/bold red]"
        if plan.requires_confirmation
        else "[green]✓  Safe to execute[/green]"
    )

    console.print(Panel(
        f"[bold cyan]Goal:[/bold cyan] {plan.goal}\n\n"
        f"[bold]Reasoning:[/bold] {plan.reasoning}\n\n"
        f"Complexity: [{complexity_color}]{plan.estimated_complexity.upper()}[/{complexity_color}]   "
        f"Confirmation required: {confirmation_badge}",
        title="[bold green]✦ VEDA Execution Plan[/bold green]",
        border_style="green",
    ))

    tbl = Table(box=box.ROUNDED, header_style="bold magenta", show_lines=True)
    tbl.add_column("#",           style="dim",       width=3)
    tbl.add_column("Tool",        style="cyan",       width=16)
    tbl.add_column("Description", style="white",      min_width=28)
    tbl.add_column("Depends on",  style="yellow",     width=12)
    tbl.add_column("Rationale",   style="dim white",  min_width=22)

    for step in plan.steps:
        deps = ", ".join(str(d) for d in step.depends_on) if step.depends_on else "—"
        tbl.add_row(str(step.step_id), step.tool.value, step.description, deps, step.rationale)

    console.print(tbl)


def render_results(result: ExecutionResult) -> None:
    overall_color = "green" if result.status == StepStatus.SUCCESS else "red"
    overall_label = "✦ COMPLETED" if result.status == StepStatus.SUCCESS else "✦ FAILED"

    tbl = Table(box=box.ROUNDED, header_style="bold magenta", show_lines=True)
    tbl.add_column("#",      style="dim",   width=3)
    tbl.add_column("Status", width=10)
    tbl.add_column("Output / Error", min_width=40)
    tbl.add_column("ms",     style="dim",   width=8)

    status_icons = {
        StepStatus.SUCCESS: "[green]✓  ok[/green]",
        StepStatus.FAILED:  "[red]✗  fail[/red]",
        StepStatus.SKIPPED: "[yellow]⊘  skip[/yellow]",
        StepStatus.PENDING: "[dim]…[/dim]",
    }

    for r in result.step_results:
        content = r.output if r.status == StepStatus.SUCCESS else r.error
        # Truncate long outputs in the table — full output is shown per-step below
        preview = content[:200] + "…" if len(content) > 200 else content
        tbl.add_row(
            str(r.step_id),
            status_icons.get(r.status, "?"),
            preview,
            f"{r.duration_ms:.0f}",
        )

    console.print(Panel(
        tbl,
        title=f"[bold {overall_color}]{overall_label} — {result.total_duration_ms:.0f}ms total[/bold {overall_color}]",
        border_style=overall_color,
    ))

    # Print full output for successful steps that produced meaningful content
    for r in result.step_results:
        if r.status == StepStatus.SUCCESS and len(r.output) > 200:
            console.print(f"\n[dim]── Full output for step {r.step_id} ──[/dim]")
            console.print(r.output)


def ask_execute(plan: ExecutionPlan) -> bool:
    """Ask the user whether to execute the plan, with extra warning if destructive."""
    if plan.requires_confirmation:
        console.print(
            "\n[bold red]⚠  WARNING:[/bold red] This plan contains potentially destructive operations.\n"
            "   Review every step carefully before proceeding.\n"
        )

    console.print("[bold]Execute this plan?[/bold] [dim](yes / no)[/dim] ", end="")
    answer = input().strip().lower()
    return answer in ("yes", "y")


async def repl() -> None:
    console.print(Panel(
        "[bold green]VEDA[/bold green] — Virtual Execution & Decision Architecture\n"
        "[dim]Phase 3 · CLI + Planning + Execution + Memory · type 'exit' to quit[/dim]",
        border_style="green",
    ))

    with console.status("[bold green]Loading memory model…[/bold green]", spinner="dots"):
        memory = MemoryManager()

    planner  = Planner()
    executor = Executor()
    console.print("[dim]Memory ready.[/dim]\n")

    while True:
        try:
            console.print("\n[bold green]veda >[/bold green] ", end="")
            user_input = input().strip()

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[dim]Shutting down VEDA.[/dim]")
                break

            # ── 1. Retrieve relevant memories ─────────────────────────────
            memories = memory.retrieve(user_input)
            if memories:
                tbl = Table(box=box.SIMPLE, header_style="bold dim", show_lines=False)
                tbl.add_column("Score", style="dim", width=6)
                tbl.add_column("Past goal",          min_width=42)
                tbl.add_column("Status",             width=10)
                for m in memories:
                    status = "[green]✓[/green]" if m["succeeded"] else "[red]✗[/red]"
                    tbl.add_row(f"{m['score']:.2f}", m["goal"], status)
                console.print(Panel(tbl, title="[dim]✦ Memory — similar past goals[/dim]", border_style="dim"))

            context = memory.format_context(memories)

            # ── 2. Plan with memory context injected ──────────────────────
            with console.status("[bold green]Planning…[/bold green]", spinner="dots"):
                plan = await planner.plan(user_input, memory_context=context)

            render_plan(plan)

            # ── 3. Ask to execute ─────────────────────────────────────────
            if not ask_execute(plan):
                console.print("[dim]Execution skipped.[/dim]")
                continue

            # ── 4. Execute ────────────────────────────────────────────────
            with console.status("[bold green]Executing…[/bold green]", spinner="dots"):
                result = await executor.execute(plan)

            render_results(result)

            # ── 5. Store to memory (always — success or failure) ──────────
            with console.status("[bold green]Storing to memory…[/bold green]", spinner="dots"):
                memory.store(user_input, plan, result)
            console.print("[dim]✦ Stored to memory.[/dim]")

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted.[/dim]")
            break
        except ValueError as e:
            console.print(f"\n[bold red]Planner error:[/bold red] {e}")
        except Exception as e:
            console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
            
if __name__ == "__main__":
    asyncio.run(repl())