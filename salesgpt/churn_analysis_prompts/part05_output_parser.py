PART05_OUTPUT_PARSER_PROMPT = """
Please extract and display the text between the following delimiters, maintaining only the text content and any markdown formatting, without adding any additional elements:
<!-- START_SECTION: Part 5 - Winback Opportunity --> <!-- END_SECTION: Part 5 - Winback Opportunity -->
The output should contain just the text found between these delimiters, with no additional formatting, brackets, or other elements. Preserve any existing markdown formatting within the text.
Here is the content to process:
{analysis_output}
"""