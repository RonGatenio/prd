import argparse
from datetime import datetime
import os
import io
import tarfile
import docker
from docker.models.containers import Container
from docker.errors import NotFound


OUT_FOLDER = os.path.join(os.path.dirname(__file__), 'docker-out')


def generate_out_foldername(name, base_folder_path=OUT_FOLDER):
    # Get a list of existing files in the folder
    existing_files = [f for f in os.listdir(base_folder_path) if os.path.isdir(os.path.join(base_folder_path, f))]

    # Find the maximum index from existing filenames
    max_index = -1
    for filename in existing_files:
        try:
            index = int(filename.split(".")[0])  # Assumes filenames are in the format "index.extension"
            max_index = max(max_index, index)
        except ValueError:
            pass  # Ignore non-numeric filenames

    # Increment the index to get the next available index
    next_index = max_index + 1
    
    # Get the current date in the format YYYY-MM-DD
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    return os.path.join(base_folder_path, f'{next_index}.{current_date}.{name}')


def mkdir(dirpath):
    if not os.path.isdir(dirpath):
        os.mkdir(dirpath)

    return dirpath


def copy_to(container: Container, src: str|list[str], dst):
    if isinstance(src, str):
        src = [src]
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode='w') as tar:
        for s in src:
            tar.add(s, arcname=os.path.basename(s))

    assert container.put_archive(dst, tar_buf.getvalue())


def copy_from(container: Container, src: str|list[str], dst=None):
    if not dst:
        dst = generate_out_foldername(container.name)

    dirpath = mkdir(dst)
    
    if isinstance(src, str):
        src = [src]
    
    for s in src:
        try:
            bits, stat = container.get_archive(s)
            size = stat.get("size")
            size = f'{size / 0x400:,.2f} KB' if size else ''
            print(f'[^] Found file {s}\t{size}')
        except NotFound as e:
            print(f'[!] Could not find file {s}')
            continue

        tar_buf = io.BytesIO()
        for chunk in bits:
            tar_buf.write(chunk)

        tar_buf.seek(0)

        with tarfile.open(fileobj=tar_buf, mode='r') as tar:
            tar.extractall(dirpath)

    print(f'[*] Files located at {os.path.abspath(dirpath)}')


def parse_args():
    parser = argparse.ArgumentParser(description="Copy files to and from a docker")

    # Specify source paths (files/folders to copy)
    parser.add_argument("source_paths", nargs="+", help="List of files/folders to copy")

    # Specify destination path (where to copy)
    parser.add_argument("-o", "--output", dest="destination_path", required=False,
                        help="Remote folder to copy local files to")

    return parser.parse_args()


def main():
    client = docker.from_env()
    container, = client.containers.list()
    
    args = parse_args()
    
    if args.destination_path:
        copy_to(container, args.source_paths, args.destination_path)
    else:
        copy_from(container, args.source_paths)


if __name__ == '__main__':
    main()
