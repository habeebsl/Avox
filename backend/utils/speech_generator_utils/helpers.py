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


async def map_timestamps_to_transcript(transcript: str, aligned_words: list[ForcedAlignmentWordResponseModel]):
    result = []
    word_index = 0
    transcript_sentences = transcript.split("\n")
    filtered_aligned_words = [
        w for w in aligned_words
        if not w.text.isspace()
    ]

    for i, sentence in enumerate(transcript_sentences):
        words_in_sentence = sentence.split()
        sentence_words = filtered_aligned_words[word_index : word_index + len(words_in_sentence)]

        if not sentence_words:
            continue

        start_time = sentence_words[0].start
        end_time = sentence_words[-1].end

        result.append({
            "text": sentence,
            "start": start_time,
            "end": end_time
        })

        word_index += len(words_in_sentence)

    return result