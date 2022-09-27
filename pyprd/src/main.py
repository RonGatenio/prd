from hbg_trace_parser import TraceParser
from pdg import generate_mock_pdg


def main():
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe.txt')
    
    import time
    
    s = time.time()
    hbg = trace.parse(False).build()
    print(f'hbg {time.time() - s} sec')
    
    s = time.time()
    pdg = generate_mock_pdg(hbg)
    print(f'pdg {time.time() - s} sec')
    
    import ipdb; ipdb.set_trace()

if __name__ == "__main__":
    main()
