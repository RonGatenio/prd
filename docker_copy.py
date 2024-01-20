import os
import sys
import io
import tarfile
import docker


def mkdir(dirpath):
    if not os.path.isdir(dirpath):
        os.mkdir(dirpath)


def copy_to(container, src, dst):
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode='w') as tar:
        tar.add(src, arcname=os.path.basename(src))

    assert container.put_archive(dst, tar_buf.getvalue())


def copy_from(container, src, dst=None):
    if not dst:
        dst = os.path.basename(src)
        dst = os.path.join(os.path.dirname(__file__), container.name, dst)

    mkdir(os.path.dirname(dst))

    bits, stat = container.get_archive(src)

    tar_buf = io.BytesIO()
    for chunk in bits:
        tar_buf.write(chunk)

    tar_buf.seek(0)

    with tarfile.open(fileobj=tar_buf, mode='r') as tar:
        tar.extractall(os.path.dirname(dst))


def main():
    client = docker.from_env()
    container, = client.containers.list()

    if len(sys.argv) == 2:
        copy_from(container, sys.argv[1])
    else:
        copy_to(container, sys.argv[1], sys.argv[2])


if __name__ == '__main__':
    main()
