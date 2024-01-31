#include <iostream>

using namespace std;

#ifdef __cplusplus
extern "C" {
#endif

void log_instruction(unsigned id);

#ifdef __cplusplus
}  // extern "C"
#endif


void log_instruction(unsigned id)
{
    std::cout << "Executing instruction " << id << std::endl;
}



