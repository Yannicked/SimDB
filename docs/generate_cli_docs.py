import os


def run_command(cmd: str) -> str:
    stream = os.popen(cmd)
    output = stream.read()
    return output


def extract_command(line: str) -> str:
    return line.strip().removeprefix("{{").removesuffix("}}").strip()


def extract_sub_commands(output: str) -> list[str]:
    in_commands = False
    sub_commands = []
    for line in output.split("\n"):
        if in_commands and line:
            sub_commands.append(line.split()[0])
        if line == "Commands:":
            in_commands = True
    return sub_commands


def generate_block(output: str) -> str:
    return f"""
```text
{output.strip()}
```
    """


def process_cmd(cmd: str) -> str:
    print(cmd)
    output = run_command(f"simdb {cmd} --help")
    sub_commands = extract_sub_commands(output) if cmd else []

    text = generate_block(output)
    for sub_command in sub_commands:
        text += "\n" + process_cmd(f"{cmd} {sub_command}")

    return text


def process_line(line: str) -> str:
    cmd = extract_command(line)
    return process_cmd(cmd)


def main():
    with open("cli.md.in") as f_in, open("cli.md", "w") as f_out:
        for line in f_in:
            if line.startswith("{{"):
                f_out.write(process_line(line))
            else:
                f_out.write(line)


if __name__ == "__main__":
    main()
