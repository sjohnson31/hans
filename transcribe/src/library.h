#pragma once

#include <string>

#include "whisper.h"

#include "grammar-parser.h"

namespace transcribe
{
    grammar_parser::parse_state grammar_parse(std::string grammar);

    whisper_context *context_init(std::string &model_path);

    void context_free(whisper_context *ctx);

    std::string transcribe(
        whisper_context *ctx,
        // Use a raw pointer instead of a vector to ease translation between python & cpp
        const float *pcmf32_samples,
        int n_pcmf32_samples,
        /** Sample text to help with transcription */
        const std::string &initial_prompt,
        /** GBNF grammar to guide decoding */
        const std::string &gbnf_grammar,
        /** Root grammar rule to start at for transcription */
        const std::string &grammar_rule);
}