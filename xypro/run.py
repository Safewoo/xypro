import asyncio
from argparse import ArgumentParser

from loguru import logger

from xypro.proxy import create_proxy
from xypro.config import load_config


def run():
    """
    Run command

    Usage:
        xypro run -f <config_path> -b <bind_address> -p <bind_port>
    """

    parser = ArgumentParser()
    parser.add_argument("-f", "--config", type=str, help="config file path")
    parser.add_argument(
        "-b", "--bind", type=str, help="bind address", default="127.0.0.1"
    )
    parser.add_argument("-p", "--port", type=int, help="bind port", default=9898)
    args = parser.parse_args()

    if not args.config:
        parser.print_help()
        return

    loop = asyncio.new_event_loop()
    config = load_config(args.config)
    asyncio.run(create_proxy(config, (args.bind, args.port)))
    logger.info("Loaded config file")
    loop.run_forever()

if __name__ == "__main__":
    run()