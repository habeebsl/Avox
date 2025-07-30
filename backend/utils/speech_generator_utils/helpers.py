import re
from typing import Any, Dict, List
from elevenlabs import ForcedAlignmentWordResponseModel

async def stringify_voice_descriptions(voice_models: dict) -> str:
    return "\n".join(
        f"Voice: {name}\nDescription: {details['description']}\n" 
        for name, details in voice_models.items()
    )

async def remove_keys_from_dict_list(data: list[dict], to_keep: set) -> list[dict]:    
    filtered_data = [
        {k: v for k, v in item.items() if k in to_keep}
        for item in data
    ]

    return filtered_data


async def map_timestamps_to_transcript(
    transcript: str, 
    aligned_words: List[ForcedAlignmentWordResponseModel]
) -> List[Dict[str, Any]]:
    """
    Map transcript sentences (split by newlines) to their corresponding 
    aligned word timestamps.
    """
    if not aligned_words:
        return []
    
    # Split transcript into actual sentences (by newlines)
    sentences = [line.strip() for line in transcript.split('\n') if line.strip()]
    if not sentences:
        return []
    
    # Create the full aligned text by concatenating all aligned words
    aligned_text = ''.join(word.text for word in aligned_words)
    
    result = []
    aligned_pos = 0  # Current position in aligned_text
    word_idx = 0     # Current word index in aligned_words
    
    for sentence in sentences:
        # Find where this sentence starts in the aligned text
        sentence_start_pos = aligned_text.find(sentence, aligned_pos)
        if sentence_start_pos == -1:
            continue
            
        sentence_end_pos = sentence_start_pos + len(sentence)
        
        # Find the word indices that correspond to this sentence
        start_word_idx = None
        end_word_idx = None
        current_pos = 0
        
        for i, word in enumerate(aligned_words):
            word_start = current_pos
            word_end = current_pos + len(word.text)
            
            # Check if this word overlaps with our sentence
            if (word_start < sentence_end_pos and word_end > sentence_start_pos):
                if start_word_idx is None:
                    start_word_idx = i
                end_word_idx = i
            
            current_pos = word_end
        
        # Add the sentence with its timestamps
        if start_word_idx is not None and end_word_idx is not None:
            result.append({
                "text": sentence,
                "start": aligned_words[start_word_idx].start,
                "end": aligned_words[end_word_idx].end
            })
        
        aligned_pos = sentence_end_pos
    
    return result