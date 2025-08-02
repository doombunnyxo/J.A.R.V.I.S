"""Message utilities for Discord bot"""

def smart_split_message(text: str, max_length: int = 2000) -> list[str]:
    """Smart message splitting that preserves paragraphs, sentences, and links"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    remaining = text
    
    while len(remaining) > max_length:
        # Find the best split point within the limit
        chunk = remaining[:max_length]
        split_point = max_length
        
        # Try to split at paragraph breaks first (\n\n)
        last_paragraph = chunk.rfind('\n\n')
        if last_paragraph > max_length * 0.7:  # Don't make chunks too small
            split_point = last_paragraph + 2
        else:
            # Try to split at single line breaks
            last_newline = chunk.rfind('\n')
            if last_newline > max_length * 0.7:
                split_point = last_newline + 1
            else:
                # Try to split at sentence endings
                sentence_endings = ['. ', '! ', '? ']
                best_sentence_end = -1
                for ending in sentence_endings:
                    pos = chunk.rfind(ending)
                    if pos > max_length * 0.7 and pos > best_sentence_end:
                        best_sentence_end = pos + len(ending)
                
                if best_sentence_end > -1:
                    split_point = best_sentence_end
                else:
                    # Try to split at word boundaries
                    last_space = chunk.rfind(' ')
                    if last_space > max_length * 0.7:
                        split_point = last_space + 1
                    else:
                        # Last resort: split at character limit but avoid breaking URLs
                        url_start = chunk.rfind('http', max(0, max_length - 200))
                        if url_start != -1:
                            # Find the end of the URL
                            url_part = remaining[url_start:]
                            url_end = url_part.find(' ')
                            if url_end == -1:
                                url_end = url_part.find('\n')
                            if url_end == -1:
                                url_end = len(url_part)
                            
                            # If URL would be split, move split point before it
                            if url_start + url_end > max_length:
                                split_point = url_start
                            else:
                                split_point = max_length
                        else:
                            split_point = max_length
        
        # Extract the chunk and update remaining text
        chunk_text = remaining[:split_point].rstrip()
        chunks.append(chunk_text)
        remaining = remaining[split_point:].lstrip()
    
    # Add the final chunk if there's remaining text
    if remaining.strip():
        chunks.append(remaining.strip())
    
    return chunks


async def send_long_message(channel, text: str, max_length: int = 2000):
    """Send a long message using smart splitting"""
    chunks = smart_split_message(text, max_length)
    for chunk in chunks:
        await channel.send(chunk)