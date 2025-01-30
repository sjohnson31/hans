#include <iostream>
#include <string>

#include "whisper.h"
#include "grammar-parser.h"
#include "library.h"

namespace transcribe
{
    grammar_parser::parse_state grammar_parse(std::string grammar)
    {
        return grammar_parser::parse(grammar.c_str());
    }

    whisper_context *context_init(std::string &model_path)
    {
        auto params = whisper_context_default_params();
        return whisper_init_from_file_with_params(model_path.c_str(), params);
    }

    void context_free(whisper_context *ctx)
    {
        whisper_free(ctx);
    }

    std::string transcribe(
        whisper_context *ctx,
        // Use a raw pointer instead of a vector to ease translation between python & cpp
        const float *pcmf32_samples,
        int n_pcmf32_samples,
        /** Sample text to help with transcription */
        const std::string &initial_prompt,
        /** GBNF grammar to guide decoding */
        const std::string &gbnf_grammar,
        /** Root grammar rule for transcription */
        const std::string &grammar_rule)
    {
        whisper_full_params params = whisper_full_default_params(WHISPER_SAMPLING_BEAM_SEARCH);
        params.print_progress = false;
        params.print_timestamps = false;
        params.no_timestamps = true;
        params.single_segment = true;
        // TODO: This seems weird??
        params.max_tokens = 200;

        // Copied from whisper.cpp/examples/command/command.cpp
        params.temperature = 0.4f;
        params.temperature_inc = 1.0f;
        params.beam_search.beam_size = 5;

        params.initial_prompt = initial_prompt.c_str();

        // TODO: Don't parse the grammar every time
        const grammar_parser::parse_state grammar_parsed = grammar_parser::parse(gbnf_grammar.c_str());
        auto grammar_rules = grammar_parsed.c_rules();
        if (grammar_parsed.rules.empty())
        {
            // TODO: Better
            return "";
        }

        params.grammar_rules = grammar_rules.data();
        params.n_grammar_rules = grammar_rules.size();
        params.i_start_rule = grammar_parsed.symbol_ids.at(grammar_rule);
        params.grammar_penalty = 100.0f;

        if (whisper_full(ctx, params, pcmf32_samples, n_pcmf32_samples) != 0)
        {
            // TODO: Better
            return "";
        }

        std::string result;
        const int n_segments = whisper_full_n_segments(ctx);
        for (int i = 0; i < n_segments; ++i)
        {
            const char *text = whisper_full_get_segment_text(ctx, i);
            result += text;
        }

        return result;
    }
}