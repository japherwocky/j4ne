from rich.console import Console
import asyncio
import logging

# Instantiate Rich Console
console = Console()

async def chat_loop():
    """
    Async chat loop that lets the user interact with the CLI in real time.
    """
    console.print("[bold cyan]Welcome to the chat CLI![/] Type '[green]exit[/]' to quit.")

    while True:
        message = await asyncio.to_thread(input, "> ")  # Use asyncio to avoid blocking
        if message.strip().lower() == "exit":
            console.print("[bold yellow]Goodbye![/]")
            break
        # Simulate processing of the message (replace with real logic)
        console.print(f"[bold green]Echo:[/] {message}")
        logging.debug(f"User input: {message}")

async def EmCeePee():
    logging.info("Launching Direct Tools Client")

    from tools.direct_client import DirectClient
    client = DirectClient()

    try:
        await client.connect_to_server()  # This is a no-op in the direct implementation
        await client.chat_loop()
    finally:
        await client.cleanup()

