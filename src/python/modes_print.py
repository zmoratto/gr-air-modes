#
# Copyright 2010 Nick Foster
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


import time, os, sys
from string import split, join
import modes_parse
import math

class modes_output_print(modes_parse.modes_parse):
  def __init__(self, mypos):
    modes_parse.modes_parse.__init__(self, mypos)

  def parse(self, message):
    [msgtype, shortdata, longdata, parity, ecc, reference] = message.split()

    shortdata = long(shortdata, 16)
    longdata = long(longdata, 16)
    parity = long(parity, 16)
    ecc = long(ecc, 16)
    reference = float(reference)

    msgtype = int(msgtype)

    output = None;

    if msgtype == 0:
      output = self.print0(shortdata, parity, ecc)
    elif msgtype == 4:
      output = self.print4(shortdata, parity, ecc)
    elif msgtype == 5:
      output = self.print5(shortdata, parity, ecc)
    elif msgtype == 11:
      output = self.print11(shortdata, parity, ecc)
    elif msgtype == 16:
      output = self.print16(shortdata, parity, ecc)
    elif msgtype == 17:
      output = self.print17(shortdata, longdata, parity, ecc)
    elif msgtype == 18:
      output = self.print18(shortdata, parity, ecc)
    elif msgtype == 19:
      output = self.print19(shortdata, parity, ecc)
    elif msgtype == 20:
      output = self.print20(shortdata, parity, ecc)
    elif msgtype == 21:
      output = self.print21(shortdata, parity, ecc)
    else:
      output = "No handler for message type %s from %s" % (str(msgtype), str(ecc))

    if reference == 0.0:
      refdb = 0.0
    else:
      refdb = 10.0*math.log10(reference)

    if output is not None:
      output = "(%.0f) " % (refdb) + output
      print output

  def print0(self, shortdata, parity, ecc):
    [vs, cc, sl, ri, altitude] = self.parse0(shortdata, parity, ecc)

    retstr = "Type 0 (short A-A surveillance) from %x at %s ft" % (ecc, altitude)
    # the ri values below 9 are used for other things. might want to
    # print those someday.
    if ri == 9:
      retstr += " (speed <75kt)"
    elif ri > 9:
      retstr += " (speed " + str(75 * (1 << (ri-10))) + "-" + str(75 * (1 << (ri-9))) + "kt)"

    if vs:
      retstr += " (aircraft is on the ground)"
    return retstr

  def print4(self, shortdata, parity, ecc):
    [fs, dr, um, altitude] = self.parse4(shortdata, parity, ecc)
    retstr = "Type 4 (short surveillance altitude reply) from %x at %s ft" % (ecc, altitude)

    if fs == 1:
      retstr = retstr + " (aircraft is on the ground)"
    elif fs == 2:
      retstr = retstr + " (AIRBORNE ALERT)"
    elif fs == 3:
      retstr = retstr + " (GROUND ALERT)"
    elif fs == 4:
      retstr = retstr + " (SPI ALERT)"
    elif fs == 5:
      retstr = retstr + " (SPI)"

    return retstr

  def print5(self, shortdata, parity, ecc):
    [fs, dr, um] = self.parse5(shortdata, parity, ecc)

    retstr = "Type 5 (short surveillance ident reply) from %x with ident %s" % ( ecc, str(shortdata & 0x1FFF) );
    if fs == 1:
      retstr = retstr + " (aircraft is on the ground)"
    elif fs == 2:
      retstr = retstr + " (AIRBORNE ALERT)"
    elif fs == 3:
      retstr = retstr + " (GROUND ALERT)"
    elif fs == 4:
      retstr = retstr + " (SPI ALERT)"
    elif fs == 5:
      retstr = retstr + " (SPI)"

    return retstr

  def print11(self, shortdata, parity, ecc):
    [ca, icao24, interrogator] = self.parse11(shortdata, parity, ecc)

    return "Type 11 (all call reply) from %x in reply to interrogator %s" % ( icao24, interrogator );

  def print16(self, shortdata, parity, ecc):
    [vs, sl, ri, altitude] = self.parse16(shortdata, parity, ecc)
    return "Type 16 (long air survey) from altitude %s" % altitude;

  def print17(self, shortdata, longdata, parity, ecc):
    icao24 = shortdata & 0xFFFFFF
    subtype = (longdata >> 51) & 0x1F;

    retstr = "Type 17 (ES) "

    if subtype == 0:
      retstr += "subtype 00 (no position) not implemented"
    elif subtype == 1:
      retstr += "subtype 01 (ident D) not implemented"
    elif subtype == 2:
      retstr += "subtype 02 (ident C) not implemented"
    elif subtype == 3:
      retstr += "subtype 03 (ident B) not implemented"
    elif subtype == 4:
      msg = self.parseBDS08(shortdata, longdata, parity, ecc)
      retstr += "subtype 04 (ident A) from " + "%x" % icao24 + " with data " + msg

    elif subtype >= 5 and subtype <= 8:
      [altitude, decoded_lat, decoded_lon, rnge, bearing] = self.parseBDS06(shortdata, longdata, parity, ecc)
      if decoded_lat is not None:
        retstr += "subtype 06 (surface report) from %x at (%.6f, %.6f) (%.2f @ %.0f)" % ( icao24, decoded_lat, decoded_lon, rnge, bearing )

    elif subtype >= 9 and subtype <= 18:
      [altitude, decoded_lat, decoded_lon, rnge, bearing] = self.parseBDS05(shortdata, longdata, parity, ecc)
      if decoded_lat is not None:
        retstr += "subtype 05 (position report) from %x at (%.6f,%.6f) (%.2f @ %.0f) at %s ft" % (icao24, decoded_lat, decoded_lon, rnge, bearing, altitude)

    elif subtype == 19:
      subsubtype = (longdata >> 48) & 0x07
      if subsubtype == 0:
        [velocity, heading, vert_spd] = self.parseBDS09_0(shortdata, longdata, parity, ecc)
        retstr += "subtype 09-0 (track report) from %x with velocity %.0f kt heading %.0f VS %.0f" % ( icao24, velocity, heading, vert_spd )

      elif subsubtype == 1:
        [velocity, heading, vert_spd] = self.parseBDS09_1(shortdata, longdata, parity, ecc)
        retstr += "subtype 09-1 (track report) from %x with velocity %.0f kt heading %.0f VS %.0f" % ( icao24, velocity, heading, vert_spd )

      else:
        retstr += "subtype 09-%i not implemented" % subsubtype
    elif subtype >= 20 and subtype <= 22:
      retstr += "subtype %02i (position report) not implemented" % subtype
    elif subtype == 23:
      retstr += "subtype 23 (reserved for test purposes) not implemented"
    elif subtype == 24:
      retstr += "subtype 24 (reserved for surface system status) not implemented"
    elif subtype == 28:
      retstr += "subtype 28 (aircraft emergency priority status) not implemented"
    elif subtype == 31:
      retstr += "subtype 31 (aircraft operational status) not implemented"
    else:
      retstr += "subtype %02i not implemented" % subtype

    return retstr

  def print18(self, shortdata, parity, ecc):
    [cf, icao24] = self.parse18( shortdata, parity, ecc )
    return "Type 18 (ES / Non-Transponders) from %x" % icao24

  def print19(self, shortdata, parity, ecc):
    [af, icao24] = self.parse18( shortdata, parity, ecc )
    retstr = "Type 19 (ES / Military Application) from %x" % icao24
    if af == 0:
      retstr += " w/ Extended Squitter"
    return retstr

  def print20(self, shortdata, parity, ecc):
    [fs, dr, um, altitude] = self.parse20( shortdata, parity, ecc )
    return "Type 20 (Comm-B Altitude Reply) from altitude %i" % altitude

  def print21(self, shortdata, parity, ecc):
    [fs, dr, um, id_code] = self.parse21( shortdata, parity, ecc )
    return "Type 21 (Comm-B Identity Reply) from self ID %x" % id_code
