O QUE E ESTE ARQUIVO
================================================================================
Este arquivo apresenta a analise documental do repositorio, produzida a partir do README,
da documentacao publica, dos manifestos e dos nomes da estrutura. Ele serve para o time
conferir o que foi entendido sobre o software antes de envia-lo a uma IA.
Nao e um resultado de vulnerabilidades e nao contem o corpo do codigo-fonte humano.

ANALISE DOCUMENTAL DO SOFTWARE
================================================================================

GitHub: ageitgey/face_recognition
Repositorio: https://github.com/ageitgey/face_recognition
Commit: d50353fdcb2f0b7180281ede9121810323ca9e37
Data do commit: 2020-10-27T21:07:20Z
Link: https://github.com/ageitgey/face_recognition/tree/d50353fdcb2f0b7180281ede9121810323ca9e37

ESCOPO E METODO
Esta analise foi produzida somente a partir de README, documentacao publica, manifestos e nomes da estrutura.
O corpo do codigo-fonte humano nao foi usado para construir a especificacao ou o prompt.

SECOES IDENTIFICADAS NO README
- Face Recognition
- Features
- Find faces in pictures
- Find and manipulate facial features in pictures
- Identify faces in pictures
- Online Demos
- Installation
- Requirements
- Installation Options:
- Installing on Mac or Linux
- Installing on an Nvidia Jetson Nano board
- Installing on Raspberry Pi 2+
- Installing on FreeBSD
- Installing on Windows
- Installing a preconfigured Virtual Machine image
- Usage
- CommandLine Interface
- facerecognition command line tool
- facedetection command line tool
- Adjusting Tolerance / Sensitivity
- More Examples
- Speeding up Face Recognition
- Python Module
- Automatically find all the faces in an image
- facelocations is now an array listing the coordinates of each face!
- Automatically locate the facial features of a person in an image
- facelandmarkslist is now an array with the locations of each facial feature in each face.
- facelandmarkslist[0]['lefteye'] would be the location and outline of the first person's left eye.
- Recognize faces in images and identify who they are
- Now we can see the two face encodings are of the same person with comparefaces!

ARQUIVOS DOCUMENTAIS UTILIZADOS
- README.md
- README.rst
- README_Japanese.md
- README_Korean.md
- README_Simplified_Chinese.md
- docs\authors.rst
- docs\contributing.rst
- docs\face_recognition.rst
- docs\history.rst
- docs\index.rst
- docs\installation.rst
- docs\modules.rst
- docs\readme.rst
- docs\usage.rst
- pyproject.toml
- setup.py
- setup.cfg
- tox.ini
- requirements.txt
- requirements_dev.txt
- requirements_docs.txt

INTERPRETACAO
O sistema a ser recriado deve preservar apenas capacidades e interfaces descritas publicamente. Detalhes ausentes devem ser resolvidos com implementacao nova, segura e testavel.