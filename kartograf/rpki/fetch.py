from concurrent.futures import ThreadPoolExecutor
import pathlib
import subprocess

from kartograf.timed import timed


@timed
def fetch_rpki_db(context):
    print("Downloading RPKI Data")
    subprocess.run(["rpki-client",
                    "-d", context.data_dir_rpki
                    ], stdout=subprocess.DEVNULL)


@timed
def validate_rpki_db(context):
    print("Validating RPKI ROAs")
    files = [path for path in pathlib.Path(context.data_dir_rpki).rglob('*')
             if path.is_file() and ((path.suffix == ".roa")
                                    or (path.name == ".roa"))]

    rpki_raw_file = 'rpki_raw.json'
    result_path = f"{context.out_dir_rpki}{rpki_raw_file}"

    def process_file(file):
        return subprocess.run(["rpki-client",
                               "-j",
                               "-n",
                               "-d",
                               context.data_dir_rpki,
                               "-P",
                               context.epoch,
                               "-f",
                               file
                               ], capture_output=True).stdout

    with ThreadPoolExecutor() as executor:
        results = executor.map(process_file, files)

    with open(result_path, "w") as res_file:
        res_file.write("[")
        res_file.write(",".join([result.decode() for result in results if result]))
        res_file.write("]")

    print(f"{len(files)} raw RKPI DB entries validated and saved to {result_path}")
