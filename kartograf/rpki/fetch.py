import os
import pathlib
import subprocess

from kartograf.timed import timed


@timed
def fetch_rpki_db(context):
    print("Downloading RPKI Data")
    subprocess.run(["rpki-client",
                    "-d", context.data_dir_rpki
                    ], capture_output=True)


@timed
def validate_rpki_db(context):
    print("Validating RPKI ROAs")
    files = [path for path in pathlib.Path(context.data_dir_rpki).rglob('*')
             if os.path.isfile(path)
             and ((os.path.splitext(path)[1] == ".roa")
                  or (path.name == ".roa"))]

    rpki_raw_file = 'rpki_raw.json'
    result_path = f"{context.out_dir_rpki}{rpki_raw_file}"

    with open(result_path, "w") as res_file:
        res_file.write("[")

    count = 0
    with open(result_path, "a") as res_file:
        for file in files:
            rpki_output = subprocess.run(["rpki-client",
                                          "-j",
                                          "-n",
                                          "-d", context.data_dir_rpki,
                                          "-P", context.epoch,
                                          "-f", file
                                          ], capture_output=True).stdout.decode()

            if count > 0 and rpki_output != "":
                res_file.write(",")
            res_file.write(rpki_output)

            count += 1

    with open(result_path, "a") as res_file:
        res_file.write("]")

    print(f"{count} raw RKPI DB entries validated and saved to {result_path}")
