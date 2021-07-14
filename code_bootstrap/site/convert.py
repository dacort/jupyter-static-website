import argparse
import json
import sys
from io import TextIOWrapper


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Uniquify images in a Jupyter Notebook.",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"{parser.prog} version 1.0.0"
    )
    # parser.add_argument("files", nargs="*")
    parser.add_argument("infile", type=argparse.FileType("r"))
    parser.add_argument(
        "outfile", nargs="?", type=argparse.FileType("w"), default=sys.stdout
    )
    return parser


def uniquify_images(input_file: TextIOWrapper, output_file: TextIOWrapper):
    data = json.loads(input_file.read())
    counter = 0
    for cell in data["cells"]:
        if cell.get("cell_type") != "markdown":
            continue
        if cell.get("attachments") and cell.get("attachments").get("image.png"):
            filename = f"image_{counter:03}.png"
            cell["attachments"][filename] = cell["attachments"].pop("image.png")
            cell["source"] = [
                t.replace("(attachment:image.png)", f"(attachment:{filename})")
                for t in cell["source"]
            ]
            counter += 1

    output_file.write(json.dumps(data, indent=1))


def main() -> None:
    parser = init_argparse()
    args = parser.parse_args()
    uniquify_images(args.infile, args.outfile)


main()
