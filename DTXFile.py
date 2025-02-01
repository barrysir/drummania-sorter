from dataclasses import dataclass
import re
import io
import logging

import logging_hack

class FileReader:
    CHUNK_SIZE = 1024

    def __init__(self, fp):
        self.fp = fp
        self.chunk = ''
        self.eof = False
    
    def get_chunk(self):
        if self.chunk == '':
            self.chunk = self.fp.read(self.CHUNK_SIZE)
            if self.chunk == '':
                self.eof = True
                raise EOFError
            
            # remove comments
            lines = self.chunk.split('\n')
            for i,line in enumerate(lines):
                idx_comment = line.find(';')
                if idx_comment != -1:
                    lines[i] = line[:idx_comment]
            self.chunk = '\n'.join(lines)
        return self.chunk

    def add_chunk(self):
        new_chunk = self.fp.read(self.CHUNK_SIZE)
        if new_chunk == '':
            self.eof = True
            raise EOFError
        
        self.chunk += new_chunk

    def set_chunk(self, index):
        while True:
            chunk = self.get_chunk()
            if index < len(chunk):
                self.chunk = self.chunk[index:]
                break
            else:
                index -= len(chunk)
    
    def erase_chunk(self):
        self.chunk = ''

    def until(self, char, eof) -> str:
        result = []
        while True:
            try:
                text = self.get_chunk()
            except EOFError:
                if eof:
                    raise 
                else:
                    break

            index = text.find(char)
            if index != -1:
                self.set_chunk(index)
                result.append(text[:index])
                break
            else:
                self.erase_chunk()

            result.append(text)

        return ''.join(result)

    def fetch(self, char, eof) -> str:
        result = []
        while True:
            text = self.chunk

            index = text.find(char)
            if index != -1:
                result = [text[:index]]
                break
            else:
                try:
                    self.add_chunk()
                except EOFError:
                    if eof:
                        raise
                    else:
                        break

        return ''.join(result)

    def after(self, char, eof):
        result = self.until(char, eof=eof)
        if not self.eof:
            self.skip(len(char))
        return result

    def skip(self, num):
        self.set_chunk(num)

@dataclass
class DTXFile:
    title: str
    artist: str
    level: int

    @classmethod
    def load(cls, path):
        if isinstance(path, io.IOBase):
            return cls._load(path)
        else:
            try:
                with open(path, encoding='shift-jis') as fp:
                    return cls._load(fp)
            except UnicodeDecodeError:
                def is_utf16_le(file_path):
                    with open(file_path, 'rb') as f:
                        # Read the first two bytes
                        bom = f.read(2)
                    return bom == b'\xff\xfe'
                
                if is_utf16_le(path):
                    with open(path, encoding='utf-16-le') as fp:
                        return cls._load(fp)
                    
                with open(path, encoding='utf-8') as fp:
                    return cls._load(fp)

                raise Exception("Couldn't determine encoding")

    @classmethod
    def _load(cls, fp):
        tags = {'title': '', 'artist': '', 'level': 0}
        tags_needed = {'title', 'artist', 'level'}

        for name,val in cls._iter_tags(fp):
            if name.upper() == 'TITLE':
                tags['title'] = val
                tags_needed.remove('title')
            elif name.upper() == 'ARTIST':
                tags['artist'] = val
                tags_needed.remove('artist')
            elif name.upper() == 'DLEVEL':
                tags['level'] = int(val)
                tags_needed.remove('level')
            elif name.upper() in ('GLEVEL', 'BLEVEL'):
                # it's a guitar chart, skip processing it
                logging_hack.warning(f"Guitar/bass chart detected (tag {name.upper()!r} found), skipping")
                return None
            
            if len(tags_needed) == 0:
                break

        if len(tags_needed) > 0:
            logging_hack.warning(f"TAGS MISSING: {tags_needed}")
        
        return cls(**tags)

    @staticmethod
    def _iter_tags(fp):
        reader = FileReader(fp)
        try:
            _ = reader.after("#", eof=True)
            while True:
                line = reader.fetch('\n', eof=True)

                # try to find colon on the same newline
                colon = line.find(':')
                if colon != -1:
                    # parse with colon as separator
                    name = line[:colon]
                    value = line[colon+1:]
                    reader.skip(len(line))
                    reader.after("#", eof=False)
                else:
                    # if colon is not found, parse until the next space
                    space = line.find(' ')
                    if space == -1:
                        raise ValueError()
                    # parse with space as separator
                    name = line[:space]
                    value = line[space+1:]
                    reader.skip(len(line))
                    reader.after("#", eof=False)

                name = name.strip()
                value = value.strip()
                yield (name, value)
        except EOFError:
            pass
