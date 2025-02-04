#include <iostream>
#include <string>
#include <cmath>

#include "whisper.h"
#include "grammar-parser.h"
#include "library.h"

namespace whisppy
{
    grammar_parser::parse_state grammar_parse(std::string grammar)
    {
        return grammar_parser::parse(grammar.c_str());
    }

    whisper_context *context_init(std::string &model_path)
    {
        return whisper_init_from_file(model_path.c_str());
    }

    void context_free(whisper_context *ctx)
    {
        whisper_free(ctx);
    }

    std::string transcribe(
        whisper_context *ctx,
        // Use a raw pointer instead of a vector to ease translation between python & cpp
        const float *pcmf32_samples,
        const int n_pcmf32_samples,
        /** Sample text to help with transcription */
        const std::string &initial_prompt,
        /** Grammar to guide transcription */
        const grammar_parser::parse_state &grammar,
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

        if (grammar.rules.empty())
        {
            // TODO: Better
            return "";
        }

        auto grammar_rules = grammar.c_rules();
        params.grammar_rules = grammar_rules.data();
        params.n_grammar_rules = grammar_rules.size();
        params.i_start_rule = grammar.symbol_ids.at(grammar_rule);
        params.grammar_penalty = 100.0f;

        if (whisper_full(ctx, params, pcmf32_samples, n_pcmf32_samples) != 0)
        {
            // TODO: Better
            return "";
        }

        std::string result;
        const int n_segments = whisper_full_n_segments(ctx);
        float logprob_min = 0.0f;
        float logprob_sum = 0.0f;

        for (int i = 0; i < n_segments; ++i)
        {
            const char *text = whisper_full_get_segment_text(ctx, i);

            result += text;

            const int n = whisper_full_n_tokens(ctx, i);
            for (int j = 0; j < n; ++j)
            {
                const auto token = whisper_full_get_token_data(ctx, i, j);

                if (token.plog > 0.0f)
                    exit(0);
                logprob_min = std::min(logprob_min, token.plog);
                logprob_sum += token.plog;
            }
        }

        fprintf(stderr, "logprob_min: %f, logprob_sum: %f\n", logprob_min, logprob_sum);
        float p_min = 100.0f * std::exp(logprob_min);
        float p_sum = 100.0f * std::exp(logprob_sum);
        fprintf(stderr, "probability_min: %f, prob_sum: %f\n", p_min, p_sum);

        // TODO: Return the probability instead of making the decision here
        if (p_min < 99.0f)
        {
            return "";
        }

        return result;
    }
}