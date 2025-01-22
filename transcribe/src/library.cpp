#include <iostream>
#include <string>

#include "grammar-parser.h"
#include "library.h"

namespace hans_transcribe
{
    int verify_grammar(std::string grammar)
    {
        const grammar_parser::parse_state grammar_parsed = grammar_parser::parse(grammar.c_str());
        if (grammar_parsed.rules.empty())
        {
            std::cout << "Failed to parse grammar" << std::endl;
            return -1;
        }

        fprintf(stderr, "%s: grammar:\n", __func__);
        grammar_parser::print_grammar(stderr, grammar_parsed);
        fprintf(stderr, "\n");

        return 0;
    }
}