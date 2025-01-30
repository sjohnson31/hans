#include <iostream>
#include <string>

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include "whisper.h"

#include "library.h"
#include "grammar-parser.h"

namespace py = pybind11;

struct whisper_context_wrapper
{
  whisper_context *ptr;
};

whisper_context_wrapper context_init_wrapper(std::string &model_path)
{
  struct whisper_context_wrapper ctx_w;
  ctx_w.ptr = transcribe::context_init(model_path);
  return ctx_w;
}

void context_free_wrapper(struct whisper_context_wrapper ctx_w)
{
  transcribe::context_free(ctx_w.ptr);
}

std::string transcribe_wrapper(
    whisper_context_wrapper *ctx,
    py::array_t<float, py::array::c_style> samples,
    /** Sample text to help with transcription */
    const std::string &initial_prompt,
    /** GBNF grammar to guide decoding */
    const std::string &gbnf_grammar,
    /** Root grammar rule to start at for transcription */
    const std::string &grammar_rule)
{
  py::buffer_info buf = samples.request();
  float *samples_ptr = static_cast<float *>(buf.ptr);
  size_t sample_count = samples.size();
  return transcribe::transcribe(ctx->ptr, samples_ptr, sample_count, initial_prompt, gbnf_grammar, grammar_rule);
}

PYBIND11_MODULE(_core, m)
{
  m.doc() = "hans transcribe";

  py::class_<whisper_context_wrapper>(m, "WhisperContext");
  py::class_<grammar_parser::parse_state>(m, "ParsedGrammar");

  m.def("grammar_parse", &transcribe::grammar_parse, R"pbdoc(
      Parse the given ebnf grammar
    )pbdoc");

  m.def("context_init", &context_init_wrapper, R"pbdoc(
      Create transcription context
    )pbdoc");

  m.def("context_free", &context_free_wrapper, R"pbdoc(
      Free transcription context
    )pbdoc");

  m.def("transcribe", &transcribe_wrapper, R"pbdoc(
      Transcribe the thing
    )pbdoc");
}
