import argparse
import sqlite3
import sys

conn = sqlite3.connect("sim.db")


def create_db():
    with open("create.sql") as file:
        sql = file.readlines()
    conn.executescript("".join(sql))


def drop_db():
    with open("drop.sql") as file:
        sql = file.readlines()
    conn.executescript("".join(sql))


def main(args: list[str]):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["create", "drop"])
    parsed_args = parser.parse_args(args)

    if parsed_args.command == "create":
        create_db()
    elif parsed_args.command == "drop":
        drop_db()


if __name__ == "__main__":
    main(sys.argv[1:])
