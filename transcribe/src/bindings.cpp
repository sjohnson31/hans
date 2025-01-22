#include <iostream>
#include <string>
#include <pybind11/pybind11.h>

#include "library.h"

namespace py = pybind11;

PYBIND11_MODULE(_core, m)
{
    m.doc() = "hans transcribe";

    m.def("verify_grammar", &transcribe::verify_grammar, R"pbdoc(
      Verify the given ebnf grammar
    )pbdoc");
}
