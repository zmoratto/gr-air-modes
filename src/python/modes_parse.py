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
from altitude import decode_alt
from cpr import cpr_decode
import math

class modes_parse:
  def __init__(self, mypos):
    self.my_location = mypos

  # Mode-S, message 0
  def parse0(self, shortdata, parity, ecc):
    # Vertical Status (airborne when 0)
    vs = bool(shortdata >> 26 & 0x1)
    # Crosslink Capability
    cc = bool(shortdata >> 25 & 0x1)
    #Sensitivity level of onboard TCAS system. 0 means no TCAS
    #sensitivity reported, 1-7 give TCAS sensitivity
    sl = shortdata >> 21 & 0x07
    # Reply Information. 0 = no onboard TCAS, 1 = NA, 2 = TCAS w/inhib
    # res, 3 = TCAS w/vert only, 4 = TCAS w/vert+horiz, 5-7 = NA, 8 =
    # no max A/S avail, 9 = A/S <= 75kt, 10 = A/S (75-150]kt, 11 =
    # (150-300]kt, 12 = (300-600]kt, 13 = (600-1200]kt, 14 = >1200kt,
    # 15 = NA
    ri = shortdata >> 15 & 0x0F

    altitude = decode_alt(shortdata & 0x1FFF, True) #bit 13 is set for type 0

    return [vs, cc, sl, ri, altitude]

  # Mode-S, message 4
  def parse4(self, shortdata, parity, ecc):
    # Flight status. 0 is airborne normal, 1 is ground normal, 2 is
    # airborne alert, 3 is ground alert, 4 is alert SPI, 5 is normal
    # SPI
    fs = shortdata >> 24 & 0x07
    # Downlink Request. 0 means no req, bit 0 is Comm-B msg rdy bit,
    # bit 1 is TCAS info msg rdy, bit 2 is Comm-B bcast #1 msg rdy,
    # bit2+bit0 is Comm-B bcast #2 msg rdy,OB bit2+bit1 is TCAS info
    # and Comm-B bcast #1 msg rdy, bit2+bit1+bit0 is TCAS info and
    # Comm-B bcast #2 msg rdy, 8-15 N/A, 16-31 req to send N-15
    # segments
    dr = shortdata >> 19 & 0x1F
    # Utility Message
    um = shortdata >> 13 & 0x3F

    altitude = decode_alt(shortdata & 0x1FFF, True)
    return [fs, dr, um, altitude]

  # Mode-S, message 5
  def parse5(self, shortdata, parity, ecc):
    # Flight status. 0 is airborne normal, 1 is ground normal, 2 is
    # airborne alert, 3 is ground alert, 4 is alert SPI, 5 is normal
    # SPI
    fs = shortdata >> 24 & 0x07
    # Downlink Request. 0 means no req, bit 0 is Comm-B msg rdy bit,
    # bit 1 is TCAS info msg rdy, bit 2 is Comm-B bcast #1 msg rdy,
    # bit2+bit0 is Comm-B bcast #2 msg rdy,OB bit2+bit1 is TCAS info
    # and Comm-B bcast #1 msg rdy, bit2+bit1+bit0 is TCAS info and
    # Comm-B bcast #2 msg rdy, 8-15 N/A, 16-31 req to send N-15
    # segments
    dr = shortdata >> 19 & 0x1F
    # Utility Message
    um = shortdata >> 13 & 0x3F

    # Identification (4096 code) as set by pilot.
    id_code = shortdata & 0x1FFF

    return [fs, dr, um, id_code]

  # Mode-S, message 11
  def parse11(self, shortdata, parity, ecc):
    interrogator = ecc & 0x0F

    ca = shortdata >> 24 & 0x07 #capability
    icao24 = shortdata & 0xFFFFFF

    return [ca, icao24, interrogator]

  # Mode-S, message 16
  def parse16(self, shortdata, parity, ecc):
    # Vertical Status (airborne when 0)
    vs = bool(shortdata >> 26 & 0x1)
    #Sensitivity level of onboard TCAS system. 0 means no TCAS
    #sensitivity reported, 1-7 give TCAS sensitivity
    sl = shortdata >> 21 & 0x07
    # Reply Information. 0 = no onboard TCAS, 1 = NA, 2 = TCAS w/inhib
    # res, 3 = TCAS w/vert only, 4 = TCAS w/vert+horiz, 5-7 = NA, 8 =
    # no max A/S avail, 9 = A/S <= 75kt, 10 = A/S (75-150]kt, 11 =
    # (150-300]kt, 12 = (300-600]kt, 13 = (600-1200]kt, 14 = >1200kt,
    # 15 = NA
    ri = shortdata >> 15 & 0x0F

    altitude = decode_alt(shortdata & 0x1FFF, True) #bit 13 is set for type 0
    return [vs, sl, ri, altitude]

  # Mode-S, message 17
  def parse17(self, shortdata, parity, ecc):
    ca = shortdata >> 24 & 0x07 #capability
    icao24 = shortdata & 0xFFFFFF
    return [ca, icao24]

  # Mode-S, message 18
  def parse18(self, shortdata, parity, ecc):
    cf = shortdata >> 24 & 0x07
    icao24 = shortdata & 0xFFFFFF
    return [cf, icao24]

  # Mode-S, message 20
  def parse20(self, shortdata, parity, ecc):
    # Flight status. 0 is airborne normal, 1 is ground normal, 2 is
    # airborne alert, 3 is ground alert, 4 is alert SPI, 5 is normal
    # SPI
    fs = shortdata >> 24 & 0x07
    # Downlink Request. 0 means no req, bit 0 is Comm-B msg rdy bit,
    # bit 1 is TCAS info msg rdy, bit 2 is Comm-B bcast #1 msg rdy,
    # bit2+bit0 is Comm-B bcast #2 msg rdy,OB bit2+bit1 is TCAS info
    # and Comm-B bcast #1 msg rdy, bit2+bit1+bit0 is TCAS info and
    # Comm-B bcast #2 msg rdy, 8-15 N/A, 16-31 req to send N-15
    # segments
    dr = shortdata >> 19 & 0x1F
    # Utility Message
    um = shortdata >> 13 & 0x3F

    altitude = decode_alt(shortdata & 0x1FFF, True)
    return [fs, dr, um, altitude]

  # Mode-S, message 21
  def parse21(self, shortdata, parity, ecc):
    # Flight status. 0 is airborne normal, 1 is ground normal, 2 is
    # airborne alert, 3 is ground alert, 4 is alert SPI, 5 is normal
    # SPI
    fs = shortdata >> 24 & 0x07
    # Downlink Request. 0 means no req, bit 0 is Comm-B msg rdy bit,
    # bit 1 is TCAS info msg rdy, bit 2 is Comm-B bcast #1 msg rdy,
    # bit2+bit0 is Comm-B bcast #2 msg rdy,OB bit2+bit1 is TCAS info
    # and Comm-B bcast #1 msg rdy, bit2+bit1+bit0 is TCAS info and
    # Comm-B bcast #2 msg rdy, 8-15 N/A, 16-31 req to send N-15
    # segments
    dr = shortdata >> 19 & 0x1F
    # Utility Message
    um = shortdata >> 13 & 0x3F

    # Identification (4096 code) as set by pilot.
    id_code = shortdata & 0x1FFF

    return [fs, dr, um, id_code]

  #the subtypes are:
  #0: No position information
  #1: Identification (Category set D)
  #2: Identification (Category set C)
  #3: "" (B)
  #4: "" (A)
  #5: Surface position accurate to 7.5m
  #6: "" to 25m
  #7: "" to 185.2m (0.1nm)
  #8: "" above 185.2m
  #9: Airborne position to 7.5m
  #10-18: Same with less accuracy
  #19: Airborne velocity
  #20: Airborne position w/GNSS height above earth
  #21: same to 25m
  #22: same above 25m
  #23: Reserved
  #24: Reserved for surface system status
  #25-27: Reserved
  #28: Extended squitter aircraft status
  #29: Current/next trajectory change point
  #30: Aircraft operational coordination
  #31: Aircraft operational status

  def parseBDS08(self, shortdata, longdata, parity, ecc):
    icao24 = shortdata & 0xFFFFFF

    msg = ""
    for i in range(0, 8):
      msg += self.charmap( longdata >> (42-6*i) & 0x3F)

    return msg

  def charmap(self, d):
    if d > 0 and d < 27:
      retval = chr(ord("A")+d-1)
    elif d == 32:
      retval = " "
    elif d > 47 and d < 58:
      retval = chr(ord("0")+d-48)
    else:
      retval = " "

    return retval

#lkplist is the last known position, for emitter-centered decoding. evenlist and oddlist are the last
#received encoded position data for each reporting type. all dictionaries indexed by ICAO number.
  _lkplist = {}
  _evenlist = {}
  _oddlist = {}
  _evenlist_ground = {}
  _oddlist_ground = {}

#the above dictionaries are all in the format [lat, lon, time].

  # ME type 9-18 (Aircraft Position)
  def parseBDS05(self, shortdata, longdata, parity, ecc):
    icao24 = shortdata & 0xFFFFFF

    encoded_lon = longdata & 0x1FFFF
    encoded_lat = (longdata >> 17) & 0x1FFFF
    cpr_format = (longdata >> 34) & 1

    enc_alt = (longdata >> 36) & 0x0FFF

    altitude = decode_alt(enc_alt, False)

    [decoded_lat, decoded_lon, rnge, bearing] = cpr_decode(self.my_location, icao24, encoded_lat, encoded_lon, cpr_format, self._evenlist, self._oddlist, self._lkplist, 0, longdata)

    return [altitude, decoded_lat, decoded_lon, rnge, bearing]

  # ME Type 5-8 (Surface Position)
  def parseBDS06(self, shortdata, longdata, parity, ecc):
    icao24 = shortdata & 0xFFFFFF

    encoded_lon = longdata & 0x1FFFF
    encoded_lat = (longdata >> 17) & 0x1FFFF
    cpr_format = (longdata >> 34) & 1
#       enc_alt = (longdata >> 36) & 0x0FFF

    altitude = 0

    [decoded_lat, decoded_lon, rnge, bearing] = cpr_decode(self.my_location, icao24, encoded_lat, encoded_lon, cpr_format, self._evenlist_ground, self._oddlist_ground, self._lkplist, 1, longdata)

    return [altitude, decoded_lat, decoded_lon, rnge, bearing]

  # ME Type 19 (Velocity subtype 0)
  def parseBDS09_0(self, shortdata, longdata, parity, ecc):
    icao24 = shortdata & 0xFFFFFF
    vert_spd = ((longdata >> 6) & 0x1FF) * 32
    ud = bool((longdata >> 15) & 1)
    if ud:
      vert_spd = 0 - vert_spd
    turn_rate = (longdata >> 16) & 0x3F
    turn_rate = turn_rate * 15/62
    rl = bool((longdata >> 22) & 1)
    if rl:
      turn_rate = 0 - turn_rate
    ns_vel = (longdata >> 23) & 0x7FF - 1
    ns = bool((longdata >> 34) & 1)
    ew_vel = (longdata >> 35) & 0x7FF - 1
    ew = bool((longdata >> 46) & 1)
    subtype = (longdata >> 48) & 0x07

    velocity = math.hypot(ns_vel, ew_vel)
    if ew:
      ew_vel = 0 - ew_vel
    if ns:
      ns_vel = 0 - ns_vel
    heading = math.atan2(ew_vel, ns_vel) * (180.0 / math.pi)
    if heading < 0:
      heading += 360

        #retstr = "Type 17 subtype 09-0 (track report) from " + "%x" % icao24 + " with velocity " + "%.0f" % velocity + "kt heading " + "%.0f" % heading + " VS " + "%.0f" % vert_spd

    return [velocity, heading, vert_spd]

  # ME Type 19 (Velocity subtype 1)
  def parseBDS09_1(self, shortdata, longdata, parity, ecc):
    icao24 = shortdata & 0xFFFFFF
    alt_geo_diff = longdata & 0x7F - 1
    above_below = bool((longdata >> 7) & 1)
    if above_below:
      alt_geo_diff = 0 - alt_geo_diff;
    vert_spd = float((longdata >> 10) & 0x1FF - 1)
    ud = bool((longdata >> 19) & 1)
    if ud:
      vert_spd = 0 - vert_spd
    vert_src = bool((longdata >> 20) & 1)
    ns_vel = float((longdata >> 21) & 0x3FF - 1)
    ns = bool((longdata >> 31) & 1)
    ew_vel = float((longdata >> 32) & 0x3FF - 1)
    ew = bool((longdata >> 42) & 1)
    subtype = (longdata >> 48) & 0x07

    if subtype == 0x02:
      ns_vel *= 4
      ew_vel *= 4

    vert_spd *= 64
    alt_geo_diff *= 25

    velocity = math.hypot(ns_vel, ew_vel)
    if ew:
      ew_vel = 0 - ew_vel

    if ns_vel == 0:
      heading = 0
    else:
      heading = math.atan(float(ew_vel) / float(ns_vel)) * (180.0 / math.pi)
    if ns:
      heading = 180 - heading
    if heading < 0:
      heading += 360

    #retstr = "Type 17 subtype 09-1 (track report) from " + "%x" % icao24 + " with velocity " + "%.0f" % velocity + "kt heading " + "%.0f" % heading + " VS " + "%.0f" % vert_spd

    return [velocity, heading, vert_spd]
