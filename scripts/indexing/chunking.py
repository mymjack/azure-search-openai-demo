import re

WHITE_SPACES = ["", " ", "\n"]
SENTENCE_ENDINGS = [",", ".", "!", "?"]
WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]


def section_by_empty_line(text, desired_section_length, combine_short_sections=True, separator_token='</?{depth}>', max_depth=99):
    """
    Splits the text into multiple sections by splitting at empty lines. Each section should be meaning wise self contained
    so there is no overlap between sections. In return the sections does not have a max length if there is no empty
    line.
    """
    wild_separator = '(' + separator_token.format(depth=r'\d+') + ')+'  # match any separator in text
    # Split text by separator token, going deeper in depth every time
    sections = [text]
    for i in range(1, max_depth+1):
        separator = separator_token.format(depth=i)  # match separator at specific depth
        new_sections = []
        for section in sections:
            if section:
                # split by separator if too long
                if len(section) > desired_section_length:
                    new_sections += re.split(separator, section)
                else:
                    new_sections.append(section)
        sections = new_sections

    # Merge shorter sections into one if needed
    if combine_short_sections:
        merged_buffer = ''
        while sections:
            section = sections.pop(0)
            if section:
                # Inner merge (merge short sections into longer paragraphs)
                while len(section) < desired_section_length:
                    # If the space cannot fit the next section, stop
                    if not sections or len(section) + len(sections[0]) + 2 > desired_section_length:
                        break
                    # If a long paragraph follows a shorter sentence, likely its a title describing a paragraph so stop
                    if len(sections) > 1 and len(sections[1]) > 4 * len(sections[0]):
                        break
                    # Merge
                    section += '\n' + sections.pop(0)
                section = re.sub(wild_separator, ' ', section)

                # Outer merge (put multiple shorter paragraphs together to save index space)
                if len(merged_buffer + ' ' + section) < desired_section_length:
                    merged_buffer += ' ' + section
                else:
                    if merged_buffer.strip():
                        yield merged_buffer.strip()
                    merged_buffer = section

                # Sections that are too long are not handled here but by chunk_by_sentence
        if merged_buffer.strip():
            yield merged_buffer.strip()
    else:
        for section in sections:
            if section.strip():
                yield re.sub(wild_separator, ' ', section.strip())


def chunk_by_sentence(text, desired_chunk_length=1000, sentence_search_limit=100, section_overlap=100):
    """
    Splits the text into multiple chunks that include overlaps between chunks. Tries to split the text at start or
    end of the sentences so to not break them, or at least the word boundary.
    """
    assert sentence_search_limit < desired_chunk_length and section_overlap < desired_chunk_length, "desired_chunk_length must be bigger than sentence_search_limit and section_overlap"
    length = len(text)
    start = 0
    end = length

    while start + section_overlap < length:
        last_word = -1
        last_sentence_end = -1
        end = start + desired_chunk_length

        if end > length:
            end = length
        else:
            # If too long, try to find the end of the sentence
            while end < length and (end - start - desired_chunk_length) < sentence_search_limit:
                if text[end] in SENTENCE_ENDINGS and text[end+1:end+2] in WHITE_SPACES:
                    last_sentence_end = end
                    break
                elif text[end] in WORDS_BREAKS:
                    last_word = end
                end += 1
            if last_sentence_end > 0:
                end = last_sentence_end  # Split at end of sentence
            elif last_word > 0:
                end = last_word  # Fall back to at least keeping a whole word
        if end < length:
            end += 1

        # Try to find the start of the sentence or at least a whole word boundary
        last_word = -1
        last_sentence_start = -1
        while start > 0 and start > end - desired_chunk_length - 2 * sentence_search_limit:
            if text[start] in SENTENCE_ENDINGS and text[start+1:start+2] in WHITE_SPACES:
                last_sentence_start = start+1
                break
            elif text[start] in WORDS_BREAKS:
                last_word = start
            start -= 1
        if last_sentence_start > 0:
            start = last_sentence_start  # Split at start of sentence
        elif last_word > 0:
            start = last_word
        if start > 0:
            start += 1

        section_text = text[start:end].strip()
        if section_text:
            yield section_text
        start = end - section_overlap

    if start + section_overlap < end:
        section_text = text[start:end].strip()
        if section_text:
            yield section_text


# Main function
def chunk_text(text, desired_chunk_length=1000, sentence_search_limit=100, section_overlap=100, combine_short_sections=True, separator_token='</?{depth}>', max_depth=99):
    """
    Tries to section text first by hierarchical structure. If each section is still too long, split the sections into
    smaller chunks with overlap. Tries its best to break at paragraphs, or sentences, or at worst at words.
    :param text:                    text to split
    :param desired_chunk_length:    desired chunk length in char
    :param sentence_search_limit:   max chars to look ahead or behind to complete the sentence at split
    :param section_overlap:         same chars to keep at end of previous chunk and beginning of next chunk
    :param combine_short_sections:  if some chunks are very short, combine them into a longer chunk (separated by \n\n)
    :param separator_token:         The separation token with depth encoding. e.g. </?{depth}> e.g. <1></1>
    :param max_depth:               max depth to look into
    :return:                        Split chunks
    """
    for section in section_by_empty_line(text, desired_chunk_length, combine_short_sections, separator_token, max_depth):
        if len(section) <= desired_chunk_length:
            yield section.strip().replace('B M O', 'BMO')
        else:
            for chunk in chunk_by_sentence(section, desired_chunk_length, sentence_search_limit, section_overlap):
                yield chunk.strip().replace('B M O', 'BMO')


if __name__ == '__main__':
    # text = "Winged male which behold all our let was rule likeness he whales saying make over blessed whales won't said sixth i doesn't Green creeping. Great fourth sea creature. To waters void and tree thing multiply which had seasons made. Moved multiply behold. Image and fowl thing bearing can't were his seed shall day day meat of void cattle shall a said created open void day itself he abundantly i. Over. Cattle forth moving earth gathering moving the very forth third. Moving dominion midst which stars years fish they're you upon signs, whose, be greater third, created itself cattle created spirit."
    # print(list(chunk_text(text, 100, 50, 10)))

    with open(r'D:\Workspace\BMO\azure-search-openai-demo\data\BMOcomCloned\main\personal\bank-accounts.txt', encoding='utf8') as f:
        text = f.read()
    # with open(r'D:\Workspace\BMO\azure-search-openai-demo\data\BMOcomCloned\pdfs\pdf\price-change-2023-en.txt', encoding='utf8') as f:
    #     text = f.read()
    [print(x + '\n\n#####################\n\n') for x in list(chunk_text(text, 1500, 100, 300))]
