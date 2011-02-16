#!/usr/bin/env python
# ---------------------------------------------------------------------------------------------
# Copyright (c) 2011-2012, Ryan Galloway (ryan@rsgalloway.com)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  - Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
#  - Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  - Neither the name of the software nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ---------------------------------------------------------------------------------------------
# docs and latest version available for download at
#   http://pyseq.googlecode.com
# ---------------------------------------------------------------------------------------------

__author__ = "Ryan Galloway <ryan@rsgalloway.com>"
__version__ = "0.1.2"

import os
import re
import sys
import logging

from datetime import datetime

gFormat = '%(length)04s %(head)s%(padding)s%(tail)s%(spacing)s%(framerange)s'
gRegex = re.compile(r'\d+')

__all__ = ['File', 'Sequence', 'getSequences']

log = logging.getLogger('pyseq')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)

# -----------------------------------------------------------------------------
class File(str):
    """sequence member file class"""
    def __init__(self, name):
        self.__filename = name
        self.__digits = gRegex.findall(self.name)
        self.__parts = gRegex.split(self.name)
        
    def __str__(self):
        return str(self.name)
    
    def __repr__(self):
        return '<pyseq.File "%s">' % self.name
   
    def _get_filename(self):
        return self.__filename
    
    def _get_digits(self):
        return self.__digits
    
    def _get_parts(self):
        return self.__parts
        
    def _set_readonly(self, value):
        raise TypeError, 'readonly attribute'
        
    name = property(_get_filename, _set_readonly)
    digits = property(_get_digits, _set_readonly)
    parts = property(_get_parts, _set_readonly)
            
    def isSibling(self, fileObject):
        """returns True if this file and fileObject are sequence siblings"""

        def _diff(fileObject):
            l1 = self.digits
            l2 = fileObject.digits
            try:
                if len(l1) == len(l2):
                    d1 = [i for i in l1 if i != l2[l1.index(i)]]
                    d2 = [i for i in l2 if i != l1[l2.index(i)]]
                    if len(d1) > 1 or len(d2) > 1:
                        return {}
                else:
                    return {}
            except IndexError, e:
                pass
            r = {}
            if (d1 and d2) and len(d1) == len(d2):
                for el in d1:
                    r[self.name.index(el)] = (el, d2[d1.index(el)])
            return r
        
        assert type(fileObject) == File, 'expecting File type, found %s' % type(fileObject)
        d = _diff(fileObject)
        log.debug('files: %s %s' %(self, fileObject))
        log.debug('diffs: %s' % d)
        log.debug('-'*75)
        return (len(d) == 1) and (self.parts == fileObject.parts)

class Sequence(list):
    """
    extends list class with methods that handle sequentialness, for example:
    
    >>> s = Sequence(['file.0001.jpg', 'file.0002.jpg', 'file.0003.jpg'])
    >>> print s
       3 file.%04d.jpg      1-3
    >>> s.append('file.0006.jpg')
    >>> print s
       4 file.%04d.jpg      1-3 6
    >>> s.contains('file.0009.jpg')
    True
    >>> s.contains('file.0009.pic')
    False
    """
    def __init__(self, filenames):
        super(Sequence, self).__init__(map(File, filenames))

    def __attrs__(self):
        return {
            'length': self.length(),
            'frames': self.frames(),
            'missing': self.missing(),
            'padding': self._get_padding(),
            'framerange': self._get_framerange(),
            'head': self.head(),
            'tail': self.tail(),
            'spacing': '\t'* (1 + (1 * (12 > len(self[0].name))))
            }
        
    def __str__(self):
        return gFormat % self.__attrs__()

    def __repr__(self):
        return '<pyseq.Sequence "%(head)s%(framerange)s%(tail)s">' % self.__attrs__()
    
    def length(self):
        """returns the length of the sequence"""
        return len(self)

    def frames(self):
        """returns list of files in sequence"""
        return map(int, self._get_frames())

    def missing(self):
        """returns list of missing files"""
        return map(int, self._get_missing())

    def head(self):
        """returns string before the seq number"""
        if len(self) > 1:
            return str(self[0]).split(self._get_frames()[0])[0]
        return self[0].name
    
    def tail(self):
        """returns string after the seq number"""
        if len(self) > 1:
            return str(self[0]).split(self._get_frames()[0])[-1]
        return ''

    def append(self, filename):
        super(Sequence, self).append(File(filename))
        
    def contains(self, fileObject):
        """checks for sequence membership"""
        if len(self) > 0:
            if type(fileObject) is not File:
                fileObject = File(fileObject)
            return self[0].isSibling(fileObject)
        
    def _get_padding(self):
        """returns padding string, e.g. %07d"""
        if len(self) > 1:
            pad = len(self._get_frames()[0])
            if pad < 2:
                return '%d'
            return '%%%02dd' % pad
        return ''
    
    def _get_framerange(self):
        """returns frame range string, e.g. 1-500"""
        frange = []
        start = ''
        end = ''
        prev = ''
        for i in range(len(self.frames())):
            if int(self.frames()[i]) != int(self.frames()[i-1])+1 and i != 0:
                if start != end:
                    frange.append('%s-%s' % (str(start), str(end)))
                elif start == end:
                    frange.append(str(start))
                start = end = self.frames()[i]
                continue
            if start is '' or int(start) > int(self.frames()[i]):
                start = self.frames()[i]
            if end is '' or int(end) < int(self.frames()[i]):
                end = self.frames()[i]
        if start == end:
            frange.append(str(start))
        else:
            frange.append('%s-%s' % (str(start), str(end)))
        return ' '.join(frange)
    
    def _get_frames(self):
        frames = []
        if len(self) > 1:
            digitSet = set(self[0].digits)
            for next in self:
                frames.extend(list(digitSet.symmetric_difference(next.digits)))
            frames = list(set(frames))
            frames.sort()
        return frames
    
    def _get_missing(self):
        if len(self) > 1:
            frange = xrange(self.frames()[0], self.frames()[-1])
            return filter(lambda x: x not in self.frames(), frange)
        return ''
        
def getSequences(source):
    """
    returns a list of Sequence objects given a directory or list that contain
    sequential members, for example:
    
    seqs = getSequences('/directory/path/'), or
    seqs = getSequences(['fileA.1.rgb', 'fileA.2.rgb', 'fileB.1.rgb'])
    for s in seqs: print s
    ...
       1 alpha.txt
       7 bm3k.%04d.jpg      1-3 5-6 9-10
       1 file.info.03.rgb
       4 file01_%04d.rgb    40-43
       4 file02_%04d.rgb    44-47
       4 file%d.03.rgb      1-4
    """
    seqs = []
    s = datetime.now()
    
    if type(source) == list:
        files = source
    elif type(source) == str and os.path.isdir(source):
        files = os.listdir(source)
    elif not os.path.isdir(source):
        log.error('Invalid directory: %s' % source)
        return []
    else:
        raise TypeError, 'Unsupported format for source argument'
        
    files.sort()
    log.debug('Found %s files' % len(files))
    
    for filename in files:
        if len(seqs) == 0:
            seqs.append(Sequence([filename]))
        else:
            newSequence = True
            for seq in seqs:
                if seq.contains(filename):
                    seq.append(filename)
                    newSequence = False
                    log.debug('Seq "%s" contains File "%s"' %(seq.head(), filename))
                    log.debug('='*75)
                    break
            if newSequence:
                seqs.append(Sequence([filename]))
                
    log.debug('Done in %s' %(datetime.now() - s))
    return seqs
    
# -----------------------------------------------------------------------------
def main():
    import optparse
    parser = optparse.OptionParser(usage="lss [path]", version="%prog "+__version__)
    parser.add_option("-d", "--debug", dest="debug", action="store_true", default=False,
                      help="set logging level to debug")
    (options, args) = parser.parse_args()
    
    if options.debug:
        log.setLevel(logging.DEBUG)

    path = os.path.curdir
    if len(args) > 0:
        path = args[0]
    print '\n'.join([str(seq) for seq in getSequences(path)])
    return (0)

if __name__ == '__main__':
    sys.exit(main())