from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from contextlib import asynccontextmanager

from server_management import turn_server_on


THUMBSUP = "\U0001f44d"
TICK = "\u2705"
ROCKET = "\U0001F680"
CROSS = "\u274C"


def mention_from_id(id):
    return f"<@{id}>"


@asynccontextmanager
async def progress_react(ctx):
    await ctx.message.add_reaction(ROCKET)
    try:
        yield
    except Exception:
        await ctx.message.add_reaction(CROSS)
        return
    await ctx.message.add_reaction(TICK)


def setup_logging():
    logger = logging.getLogger("discord")
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
    handler.setFormatter(
        logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
    )
    logger.addHandler(handler)
    return logger


class DiscordServerBot(commands.Bot):
    """
    Manages the Discord server
    """

    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or("!"), self_bot=False)
        self.add_commands()

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    def add_commands(self):
        @self.command(name="on", pass_context=True)
        async def on(ctx, str=""):
            print("on received")
            async with progress_react(ctx):
                turn_server_on()


if __name__ == "__main__":
    load_dotenv()
    discord_token = os.getenv("DISCORD_TOKEN")

    logger = setup_logging()

    bot = DiscordServerBot()

    bot.run(discord_token)
