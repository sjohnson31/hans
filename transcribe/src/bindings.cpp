#include <iostream>
#include <string>
#include <pybind11/pybind11.h>

#include "library.h"

std::string hello_from_bin() { return "Hello from transcribe!"; }
std::string hello_from_bin_two() { return "Hello from transcribe two!"; }

namespace py = pybind11;

PYBIND11_MODULE(_core, m)
{
  m.doc() = "hans transcribe";

  m.def("hello_from_bin", &hello_from_bin, R"pbdoc(
      A function that returns a Hello string.
  )pbdoc");

  m.def("hello_from_bin_two", &hello_from_bin_two, R"pbdoc(
      A function that returns a Hello string two.
  )pbdoc");

  m.def("verify_grammar", &hans_transcribe::verify_grammar, R"pbdoc(
      Verify the given ebnf grammar
  )pbdoc");
}
