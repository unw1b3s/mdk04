"""Вывести текст предоставленного DOCX средствами стандартной библиотеки."""
import argparse
from zipfile import ZipFile
from xml.etree import ElementTree

parser = argparse.ArgumentParser()
parser.add_argument('path', help='Путь к индивидуальному листу DOCX')
args = parser.parse_args()
with ZipFile(args.path) as archive:
    root = ElementTree.fromstring(archive.read('word/document.xml'))
namespace = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
for paragraph in root.iter(namespace + 'p'):
    text = ''.join(node.text or '' for node in paragraph.iter(namespace + 't'))
    if text.strip():
        print(text)
