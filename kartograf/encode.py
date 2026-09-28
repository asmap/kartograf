"""Encode the final map with the vendored Bitcoin Core tools."""

from pathlib import Path
import subprocess
import sys

from kartograf.timed import timed


@timed
def encode_result(context):
    """Write filled and unfilled ASMaps and return their paths."""
    tool = Path(__file__).parent / "vendor" / "bitcoin_core" / "asmap-tool.py"
    output_files = []
    for suffix, fill in (("", True), ("_unfilled", False)):
        output_file = Path(context.out_dir) / f"{context.epoch}_asmap{suffix}.dat"
        print(f"Encoding {output_file.name}")
        command = [sys.executable, str(tool), "encode"]
        if fill:
            command.append("--fill")
        command.append(str(context.final_result_file))
        try:
            # Only write the result after encoding succeeds. Binary ASMaps are
            # small compared to the text input, so buffering them is inexpensive.
            result = subprocess.run(command, stdout=subprocess.PIPE, check=True)
            output_file.write_bytes(result.stdout)
        except (subprocess.CalledProcessError, OSError) as err:
            sys.exit(f"Failed to encode {output_file.name}: {err}")
        output_files.append(output_file)
    return output_files
