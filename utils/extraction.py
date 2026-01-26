#  Released under MIT License
#
#  Copyright (©) 2025. Talent Factory GmbH
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights to
#  use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
#  of the Software, and to permit persons to whom the Software is furnished to
#  do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#  OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#  NON INFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#  HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#  WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#  OR OTHER DEALINGS IN THE SOFTWARE.

import pathlib
import logging
import argparse
from datetime import datetime
from pypdf import PdfReader

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

# Logging-Konfiguration
def setup_logging(log_level=logging.INFO):
    """Konfiguriert das Logging-System."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'pdf_extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

def extract_text_with_pypdf(pdf_path, logger=None):
    """
    Extrahiert Text aus einer PDF-Datei mit pypdf als Fallback.

    Args:
        pdf_path (str): Pfad zur PDF-Datei
        logger: Logger-Instanz für Ausgaben

    Returns:
        str: Extrahierter Text im Markdown-Format
    """
    try:
        reader = PdfReader(pdf_path)
        text_content = []

        # Metadaten extrahieren
        metadata = reader.metadata
        if metadata:
            text_content.append("# Dokument-Metadaten\n")
            if metadata.title:
                text_content.append(f"**Titel:** {metadata.title}\n")
            if metadata.author:
                text_content.append(f"**Autor:** {metadata.author}\n")
            if metadata.subject:
                text_content.append(f"**Betreff:** {metadata.subject}\n")
            if metadata.creator:
                text_content.append(f"**Erstellt mit:** {metadata.creator}\n")
            text_content.append(f"**Anzahl Seiten:** {len(reader.pages)}\n")
            text_content.append("\n---\n\n")

        if logger:
            logger.info(f"Extrahiere Text aus {len(reader.pages)} Seiten")

        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text.strip():
                text_content.append(f"## Seite {page_num}\n\n{text}\n")

        return "\n".join(text_content)
    except Exception as e:
        raise Exception(f"Fehler beim Extrahieren mit pypdf: {str(e)}")

if DOCLING_AVAILABLE:
    converter = DocumentConverter()
else:
    converter = None

# --------------------------------------------------------------
# Batch PDF extraction from demo directory
# --------------------------------------------------------------

def process_pdf_files(input_dir="demo", output_dir=None, force_pypdf=False, logger=None):
    """
    Verarbeitet alle PDF-Dateien im angegebenen Verzeichnis und
    speichert sie als Markdown-Dateien.

    Args:
        input_dir (str): Pfad zum Verzeichnis mit den PDF-Dateien
        output_dir (str): Pfad zum Ausgabeverzeichnis (Standard: gleiches wie input_dir)
        force_pypdf (bool): Erzwingt die Verwendung von pypdf statt docling
        logger: Logger-Instanz für Ausgaben
    """
    input_path = pathlib.Path(input_dir)
    output_path = pathlib.Path(output_dir) if output_dir else input_path

    if logger:
        logger.info(f"Starte PDF-Verarbeitung in: {input_path}")
        logger.info(f"Ausgabeverzeichnis: {output_path}")

    if not input_path.exists():
        error_msg = f"Eingabeverzeichnis {input_dir} existiert nicht!"
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
        return False

    # Ausgabeverzeichnis erstellen falls es nicht existiert
    output_path.mkdir(parents=True, exist_ok=True)

    # Alle PDF-Dateien im Verzeichnis finden
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        error_msg = f"Keine PDF-Dateien im Verzeichnis {input_dir} gefunden!"
        if logger:
            logger.warning(error_msg)
        else:
            print(error_msg)
        return False

    use_docling = DOCLING_AVAILABLE and converter and not force_pypdf
    method = "docling" if use_docling else "pypdf"

    if logger:
        logger.info(f"Gefundene PDF-Dateien: {len(pdf_files)}")
        logger.info(f"Verwendete Methode: {method}")
    else:
        print(f"Gefundene PDF-Dateien: {len(pdf_files)}")
        print(f"Verwendete Methode: {method}")

    success_count = 0
    error_count = 0

    for i, pdf_file in enumerate(pdf_files, 1):
        try:
            if logger:
                logger.info(f"[{i}/{len(pdf_files)}] Verarbeite: {pdf_file.name}")
            else:
                print(f"\n[{i}/{len(pdf_files)}] Verarbeite: {pdf_file.name}")

            # PDF konvertieren - versuche zuerst docling, dann pypdf
            if use_docling:
                try:
                    result = converter.convert(str(pdf_file))
                    document = result.document
                    markdown_output = document.export_to_markdown()
                    if logger:
                        logger.info("Erfolgreich mit docling extrahiert")
                except Exception as docling_error:
                    if logger:
                        logger.warning(f"Docling fehlgeschlagen, verwende pypdf: {str(docling_error)}")
                    else:
                        print(f"Docling fehlgeschlagen, verwende pypdf: {str(docling_error)}")
                    markdown_output = extract_text_with_pypdf(str(pdf_file), logger)
            else:
                markdown_output = extract_text_with_pypdf(str(pdf_file), logger)

            # Markdown-Dateiname erstellen (PDF-Endung durch .md ersetzen)
            md_filename = pdf_file.stem + ".md"
            md_filepath = output_path / md_filename

            # Markdown-Datei speichern
            with open(md_filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_output)

            success_msg = f"✓ Gespeichert als: {md_filepath}"
            if logger:
                logger.info(success_msg)
            else:
                print(success_msg)

            success_count += 1

        except Exception as e:
            error_msg = f"✗ Fehler beim Verarbeiten von {pdf_file.name}: {str(e)}"
            if logger:
                logger.error(error_msg)
            else:
                print(error_msg)
            error_count += 1

    # Zusammenfassung
    summary = f"Verarbeitung abgeschlossen: {success_count} erfolgreich, {error_count} Fehler"
    if logger:
        logger.info(summary)
    else:
        print(f"\n{summary}")

    return error_count == 0

def main():
    """Hauptfunktion mit Kommandozeilenargument-Parsing."""
    parser = argparse.ArgumentParser(
        description="Extrahiert Text aus PDF-Dateien und konvertiert sie zu Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python extraction.py                         # Verarbeitet alle PDFs im demo/ Verzeichnis
  python extraction.py -i pdfs/ -o markdown/   # Spezifische Ein- und Ausgabeverzeichnisse
  python extraction.py --force-pypdf           # Erzwingt pypdf statt docling
  python extraction.py --verbose               # Detaillierte Ausgabe
        """
    )

    parser.add_argument(
        "-i", "--input-dir",
        default="demo",
        help="Eingabeverzeichnis mit PDF-Dateien (Standard: demo)"
    )

    parser.add_argument(
        "-o", "--output-dir",
        help="Ausgabeverzeichnis für Markdown-Dateien (Standard: gleiches wie Eingabe)"
    )

    parser.add_argument(
        "--force-pypdf",
        action="store_true",
        help="Erzwingt die Verwendung von pypdf statt docling"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Aktiviert detaillierte Logging-Ausgabe"
    )

    parser.add_argument(
        "--log-file",
        help="Pfad zur Log-Datei (Standard: automatisch generiert)"
    )

    args = parser.parse_args()

    # Logging konfigurieren
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logging(log_level)

    if args.log_file:
        # Zusätzlichen FileHandler für spezifische Log-Datei hinzufügen
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)

    logger.info("=== PDF-zu-Markdown Extraktion gestartet ===")
    logger.info(f"Docling verfügbar: {DOCLING_AVAILABLE}")
    logger.info(f"Eingabeverzeichnis: {args.input_dir}")
    logger.info(f"Ausgabeverzeichnis: {args.output_dir or args.input_dir}")
    logger.info(f"Erzwinge pypdf: {args.force_pypdf}")

    try:
        success = process_pdf_files(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            force_pypdf=args.force_pypdf,
            logger=logger
        )

        if success:
            logger.info("=== Alle Dateien erfolgreich verarbeitet ===")
            exit_code = 0
        else:
            logger.error("=== Verarbeitung mit Fehlern abgeschlossen ===")
            exit_code = 1

    except KeyboardInterrupt:
        logger.info("Verarbeitung durch Benutzer abgebrochen")
        exit_code = 130
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {str(e)}")
        exit_code = 1

    return exit_code

if __name__ == "__main__":
    exit(main())
