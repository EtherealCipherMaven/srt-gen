import streamlit as st
from docx import Document
import re
from datetime import timedelta
import io

def read_docx(file_like_object):
    doc = Document(file_like_object)
    paragraphs = []
    for i, para in enumerate(doc.paragraphs):
        if i < 2:
            continue
        if "PART" in para.text.upper():
            paragraphs.append({'type': 'heading', 'text': para.text})
        else:
            paragraphs.append({'type': 'normal', 'text': para.text})
    return paragraphs

def split_sentences(text):
    sentences = re.split(r'(?<=[.!?]) +', text)
    return sentences


def split_sentence_by_length(sentence, max_length=400, flex_length=5, avoid_ending_words=None):
    if avoid_ending_words is None:
        avoid_ending_words = {'the', 'a', 'an', 'for', 'by', 'and', 'in', 'on', 'at', 'to', 'of', 'as'}
    
    words = sentence.split()
    
    if len(words) <= max_length + flex_length:
        return [sentence]
    
    def find_split_point(words):
        mid_point = len(words) // 2
        
        while mid_point > 0 and words[mid_point - 1].lower() in avoid_ending_words:
            mid_point -= 1 
        
        if mid_point == 0 or mid_point == len(words): 
            mid_point = len(words) // 2
        
        return mid_point
    
    split_index = find_split_point(words)
    
    first_half = ' '.join(words[:split_index])
    second_half = ' '.join(words[split_index:])
    
    if len(second_half.split()) > max_length:
        second_half_parts = split_sentence_by_length(second_half, max_length, flex_length, avoid_ending_words)
        return [first_half] + second_half_parts
    else:
        return [first_half, second_half]



def is_acceptable_word(word):
    return word.lower() not in ['the', 'a', 'an', 'for', 'by']

def is_part_heading(text):
    return bool(re.match(r'PART\s+[IVXLC]+:\s+.*', text))


def format_subtitle(text, max_words_per_line=10):
    max_words_per_line=10
    words = text.split()
    lines = []
    avoid_ending_words = {
        'the', 'a', 'an', 'for', 'by', 'and', 'in', 'on', 'at', 'to', 'of', 'as'
    }

    if len(words) <= max_words_per_line:
        lines.append(' '.join(words))  
    else:
        split_point = (len(words) + 1) // 2  
        if words[split_point - 1].lower() in avoid_ending_words and split_point < len(words):
            split_point += 1

        split_point = min(split_point, len(words) - 1)

        first_half = ' '.join(words[:split_point])
        second_half = ' '.join(words[split_point:])

        lines.append(first_half)
        lines.append(second_half)

    formatted_subtitles = ['\n'.join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
    return formatted_subtitles



def process_paragraphs(paragraphs, max_chars=180, max_words = 22, flex_words=0):
    avoid_ending_words = {
        'the', 'a', 'an', 'for', 'by', 'and', 'in', 'on', 'at', 'to', 'of', 'as'
    }
    combined_sentences = []
    for para in paragraphs:
        if para['type'] == 'heading' and is_part_heading(para['text']):
            combined_sentences.append('NEW PART STARTS HERE')
        elif para['type'] == 'normal':
            sentences = split_sentences(para['text'])
            for sentence in sentences:
                if len(sentence.split()) > max_words:
                    split_sentences_1 = split_sentence_by_length(sentence, max_words, flex_words, avoid_ending_words)
                    combined_sentences.extend(split_sentences_1)
                else:
                    combined_sentences.append(sentence)
    return combined_sentences

def convert_to_srt(doc_path, output_path='output.srt', base_duration=10, short_duration=5, max_chars=1800, max_line_length=70):
    paragraphs = read_docx(doc_path)
    processed_entries = process_paragraphs(paragraphs=paragraphs, max_chars=max_chars)
    srt_entries = []
    start_time = timedelta(0)  
    new_part_marker_needed = False

    for entry in processed_entries:
        entry = entry.strip()  
        if entry == 'NEW PART STARTS HERE':
            new_part_marker_needed = True
        elif entry:  
            if new_part_marker_needed:
                srt_entries.append('LINE_BREAKS')
                new_part_marker_needed = False

            subtitles = format_subtitle(entry, max_line_length)
            if subtitles: 
                for subtitle in subtitles:
                    subtitle_text = subtitle.strip()  
                    if subtitle_text:
                        word_count = len(subtitle_text.split())
                        duration = short_duration if word_count < 8 else base_duration
                        end_time = start_time + timedelta(seconds=duration)
                        
                        start_str = f'{start_time.seconds//3600:02}:{(start_time.seconds//60)%60:02}:{start_time.seconds%60:02},{start_time.microseconds//1000:03}'
                        end_str = f'{end_time.seconds//3600:02}:{(end_time.seconds//60)%60:02}:{end_time.seconds%60:02},{end_time.microseconds//1000:03}'

                        srt_entry = {'start': start_str, 'end': end_str, 'text': subtitle}
                        srt_entries.append(srt_entry)
                        start_time = end_time

    with open(output_path, 'w') as f:
        i = 1
        for entry in srt_entries:
            if entry == 'LINE_BREAKS':
                f.write("\n\n\n\n\n")
            else:
                f.write(f"{i}\n{entry['start']} --> {entry['end']}\n{entry['text']}\n\n")
                i += 1

def generate_srt_content(file_like_object, base_duration=10, short_duration=5, max_chars=1800, max_line_length=70):
    paragraphs = read_docx(file_like_object)
    processed_entries = process_paragraphs(paragraphs=paragraphs, max_chars=max_chars)
    srt_content = ""
    start_time = timedelta(0)  
    new_part_marker_needed = False
    i = 1

    for entry in processed_entries:
        entry = entry.strip()  
        if entry == 'NEW PART STARTS HERE':
            new_part_marker_needed = True
        elif entry: 
            if new_part_marker_needed:
                srt_content += "\n\n\n\n\n"
                new_part_marker_needed = False

            subtitles = format_subtitle(entry, max_line_length)
            if subtitles:  
                for subtitle in subtitles:
                    subtitle_text = subtitle.strip() 
                    if subtitle_text:
                        word_count = len(subtitle_text.split())
                        duration = short_duration if word_count < 8 else base_duration
                        end_time = start_time + timedelta(seconds=duration)
                        
                        start_str = f'{start_time.seconds//3600:02}:{(start_time.seconds//60)%60:02}:{start_time.seconds%60:02},{start_time.microseconds//1000:03}'
                        end_str = f'{end_time.seconds//3600:02}:{(end_time.seconds//60)%60:02}:{end_time.seconds%60:02},{end_time.microseconds//1000:03}'

                        srt_content += f"{i}\n{start_str} --> {end_str}\n{subtitle}\n\n"
                        start_time = end_time
                        i += 1

    return srt_content

def app():
    st.title("Subtitle Generator")
    uploaded_file = st.file_uploader("Choose a .docx file")
    if uploaded_file is not None:
        srt_content = generate_srt_content(uploaded_file)
        edited_srt_content = st.text_area("Edit Subtitles", srt_content, height=600)
        if st.button("Download Edited SRT"):
            st.download_button(
                label="Download Edited SRT",
                data=edited_srt_content.encode("utf-8"),
                file_name=uploaded_file.name.replace(".docx", ".srt"),
                mime="text/plain",
            )
if __name__ == "__main__":
    app()
