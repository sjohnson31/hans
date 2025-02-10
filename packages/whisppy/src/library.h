#pragma once

#include <string>

#include "whisper.h"

#include "grammar-parser.h"

namespace whisppy
{
    grammar_parser::parse_state grammar_parse(std::string grammar);

    whisper_context *context_init(std::string &model_path);

    void context_free(whisper_context *ctx);

    std::string transcribe(
        whisper_context *ctx,
        const std::vector<float> &pcmf32,
        /** Sample text to help with transcription */
        const std::string &initial_prompt,
        /** Grammar to guide transcription */
        const grammar_parser::parse_state &grammar,
        /** Root grammar rule for transcription */
        const std::string &grammar_rule);
}