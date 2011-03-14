#!/usr/bin/env python
# Copyright 2011 Zack Moratto
#
# This file is part of gr-air-modes
#
# gr-air-modes is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# gr-air-modes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gr-air-modes; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from optparse import OptionParser
import time, os, sys, threading
from string import split, join

sys.path.append( os.path.realpath(__file__)[:-24]+"libexec")

from modes_print import modes_output_print
from modes_sql import modes_output_sql
from modes_sbs1 import modes_output_sbs1
from modes_kml import modes_kml

def raw_parse(message):
    [msgtype, shortdata, longdata, parity, ecc, reference] = message.split()
    if int(msgtype) < 12:
        print (shortdata+","+parity).upper()
    else:
        print (shortdata+","+longdata+","+parity).upper()

def hex2bin(a):
    s = ""
    a = a.upper()
    t = {'0':'0000','1':'0001','2':'0010','3':'0011',
         '4':'0100','5':'0101','6':'0110','7':'0111',
         '8':'1000','9':'1001','A':'1010','B':'1011',
         'C':'1100','D':'1101','E':'1110','F':'1111'}
    for c in a:
        s+=t[c]
    return s

def die(msg, code=-1):
    print >>sys.stderr, msg
    sys.exit(code)

# MAIN
if __name__ == '__main__':
    usage = "%prog: [options] filename"
    parser = OptionParser(usage=usage)
    parser.add_option("-p","--parser", type="string",
                      default="raw",
                      help="set the parser to use for decode input")

    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.print_help()
        die('\nERROR: Missing input files', code=2)
    print("\nParsing with: %s\n" % options.parser)

    outputs = []
    kmlgen = None
    for i in options.parser.split(','):
        if i == "raw":
            outputs.append(raw_parse)
        elif i == "print":
            outputs.append(modes_output_print([37.76225, -122.44254]).parse)
        elif i == "kml":
            sqlport = modes_output_sql([37.76225, -122.44254],'adsb.db')
            outputs.append(sqlport.insert)
            kmlgen = modes_kml('adsb.db', args[0][:-3]+"kml",
                               [37.76225, -122.44254])

    f = open(args[0],'r')
    for line in f:
        blocks = line.strip().split(',')
        if not len(blocks) == 3:
            continue
        bstring = hex2bin(blocks[2])
        format = int(bstring[:5],2)
        short = blocks[2][:8]
        longm = ""
        parity = ""
        ecc = "000000" # I don't know what this is
        reference = 0.001
        if len(blocks[2]) == 14:
            longm = "00000000000000"
            parity = blocks[2][-6:]
        else:
            longm = blocks[2][8:22]
            parity = blocks[2][-6:]
        msg = '%02i %s %s %s %s %f'%(format,short,longm,parity,ecc,reference)
        #print msg
        for out in outputs:
            out(msg)

    if kmlgen is not None:
        kmlgen.done = True
