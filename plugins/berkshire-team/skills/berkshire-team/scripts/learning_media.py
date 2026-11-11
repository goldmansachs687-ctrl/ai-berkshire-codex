"""Extract local PDF pages or transcribe a local recording without network calls."""
import argparse
import re
import subprocess
import wave
from pathlib import Path


SRT_TIME = re.compile(r'(?m)^(\d+:\d{2}:\d{2},\d{3}) --> (\d+:\d{2}:\d{2},\d{3})$')


def extract_pdf(source, output, first, last):
    from docling_parse.pdf_parser import DoclingPdfParser

    doc = DoclingPdfParser().load(source)
    if not 1 <= first <= last <= doc.number_of_pages():
        raise ValueError('PDF page numbers must be within the document and start at 1')
    parts = []
    try:
        for number in range(first, last + 1):
            page = doc.get_page(number)
            lines = '\n'.join(cell.text for cell in page.textline_cells).strip()
            if not lines:
                raise ValueError(f'PDF page {number} has no text layer; use local OCR before indexing')
            parts.append(f'===== PDF PAGE {number} =====\n{lines}')
            doc.unload_pages((number, number))
    finally:
        doc.unload()
    output.write_text('\n\n'.join(parts) + '\n', encoding='utf-8')


def srt_timestamp(value, offset, limit=None):
    h, m, s, ms = (int(part) for part in re.split('[:,]', value))
    absolute = ((h * 60 + m) * 60 + s) * 1000 + ms + offset
    if limit is not None:
        absolute = min(absolute, limit)
    seconds, ms = divmod(absolute, 1000)
    minutes, s = divmod(seconds, 60)
    h, m = divmod(minutes, 60)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def transcribe(source, output, start, end, whisper, model, language):
    import imageio_ffmpeg

    if not 0 <= start < end:
        raise ValueError('clip start and end must be increasing nonnegative seconds')
    wav = output.with_name(output.name + '.wav')
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-hide_banner', '-loglevel', 'error',
                    '-n', '-i', str(source), '-ss', str(start), '-t', str(end - start),
                    '-ac', '1', '-ar', '16000', str(wav)], check=True)
    with wave.open(str(wav)) as clip:
        if abs(clip.getnframes() / clip.getframerate() - (end - start)) > 0.1:
            raise ValueError('recording is shorter than the requested clip')
    subprocess.run([str(whisper), '-ng', '-m', str(model), '-f', str(wav), '-l', language,
                    '-osrt', '-oj', '-of', str(output)], check=True)
    srt = output.with_name(output.name + '.srt')
    transcript = srt.read_text(encoding='utf-8')
    offset, limit = round(start * 1000), round(end * 1000)
    adjusted, count = SRT_TIME.subn(
        lambda match: ' --> '.join(srt_timestamp(value, offset, limit) for value in match.groups()),
        transcript)
    if not count:
        raise ValueError('Whisper did not produce timestamped speech')
    output.with_name(output.name + '-source-time.txt').write_text(adjusted, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    pdf = commands.add_parser('pdf')
    pdf.add_argument('--first', type=int, required=True)
    pdf.add_argument('--last', type=int, required=True)
    audio = commands.add_parser('audio')
    audio.add_argument('--start', type=float, required=True)
    audio.add_argument('--end', type=float, required=True)
    audio.add_argument('--whisper', type=Path, required=True)
    audio.add_argument('--model', type=Path, required=True)
    audio.add_argument('--language', default='en')
    for command in (pdf, audio):
        command.add_argument('--source', type=Path, required=True)
        command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        source = args.source.resolve(strict=True)
        output = args.output.resolve()
        if output.exists() or not source.is_file():
            raise ValueError('provide an existing input file and a fresh output path')
        if args.command == 'pdf':
            extract_pdf(source, output, args.first, args.last)
        else:
            transcribe(source, output, args.start, args.end, args.whisper.resolve(strict=True),
                       args.model.resolve(strict=True), args.language)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
