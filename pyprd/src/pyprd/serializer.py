import os
from datetime import datetime
import dill as pickle


def save(filename=None, **kwargs):
    if not filename:
        filename = f'{datetime.now():%Y-%m-%d_%H-%M}.bin'
        filename = os.path.join(os.path.dirname(__file__), filename)

    filename = os.path.abspath(filename)

    with open(filename, 'wb') as f:
        pickle.Pickler(f).dump(kwargs)

    print(f'Saved data to {filename}')
    return filename


def load(filename):
    with open(filename, 'rb') as f:
        return pickle.Unpickler(f).load()
