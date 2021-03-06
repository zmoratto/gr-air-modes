/*
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
*/

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <air_modes_preamble.h>
#include <gr_io_signature.h>
#include <string.h>
#include <iostream>

air_modes_preamble_sptr air_make_modes_preamble(int channel_rate, float threshold_db)
{
	return air_modes_preamble_sptr (new air_modes_preamble(channel_rate, threshold_db));
}

air_modes_preamble::air_modes_preamble(int channel_rate, float threshold_db) :
    gr_block ("modes_preamble",
                   gr_make_io_signature2 (2, 2, sizeof(float), sizeof(float)), //stream 0 is received data, stream 1 is moving average for reference
                   gr_make_io_signature (1, 1, sizeof(float))) //the output packets
{
	d_chip_rate = 2000000; //2Mchips per second
	d_samples_per_chip = channel_rate / d_chip_rate; //must be integer number of samples per chip to work
	d_samples_per_symbol = d_samples_per_chip * 2;
	d_check_width = 120 * d_samples_per_symbol; //only search to this far from the end of the stream buffer
	d_threshold_db = threshold_db;
	d_threshold = powf(10., threshold_db/10.); //the level that the sample must be above the moving average in order to qualify as a pulse
	
	set_output_multiple(1+d_check_width*2);
	
	std::stringstream str;
	str << name() << unique_id();
	d_me = pmt::pmt_string_to_symbol(str.str());
	d_key = pmt::pmt_string_to_symbol("preamble_found");
	set_history(d_check_width);
}

static void integrate_and_dump(float *out, const float *in, int chips, int samps_per_chip) {
	for(int i=0; i<chips; i++) {
		float acc = 0;
		for(int j=0; j<samps_per_chip; j++) {
			acc += in[i*samps_per_chip+j];
		}
		out[i] = acc;
	}
}

//the preamble pattern in bits
//fixme goes in .h
static const bool preamble_bits[] = {1, 0, 1, 0, 0, 0, 0, 1, 0, 1};
static double correlate_preamble(const float *in, int samples_per_chip) {
	double corr = 0.0;
	for(int i=0; i<10; i++) {
		for(int j=0; j<samples_per_chip;j++)
			if(preamble_bits[i]) corr += in[i*samples_per_chip+j];
	}
	return corr;
}

int air_modes_preamble::general_work(int noutput_items,
						  gr_vector_int &ninput_items,
                          gr_vector_const_void_star &input_items,
		                  gr_vector_void_star &output_items)
{
	const float *in = (const float *) input_items[0];
	const float *inavg = (const float *) input_items[1];
	const int ninputs = std::min(ninput_items[0], ninput_items[1]); //just in case
	float *out = (float *) output_items[0];

	//fixme move into .h
	const int pulse_offsets[4] = {    0,
	                              int(2 * d_samples_per_chip),
	                              int(7 * d_samples_per_chip),
	                              int(9 * d_samples_per_chip)
	                             };

	uint64_t abs_out_sample_cnt = nitems_written(0);

	for(int i=0; i < ninputs; i++) {
		float pulse_threshold = inavg[i] * d_threshold;
		if(in[i] > pulse_threshold) { //hey we got a candidate
			if(in[i+1] > in[i]) continue; //wait for the peak
			//check to see the rest of the pulses are there
			if( in[i+pulse_offsets[1]] < pulse_threshold ) continue;
			if( in[i+pulse_offsets[2]] < pulse_threshold ) continue;
			if( in[i+pulse_offsets[3]] < pulse_threshold ) continue;

			//get a more accurate bit center by finding the correlation peak across all four preamble bits
			bool late = false;
			do {
				double now_corr = correlate_preamble(in+i, d_samples_per_chip);
				double late_corr = correlate_preamble(in+i+1, d_samples_per_chip);
				late = (late_corr > now_corr);
				if(late) i++;
			} while(late);

			//now check to see that the rest of the chips in the preamble
			//are below the peaks by threshold dB
			float avgpeak = ( in[i+pulse_offsets[0]]
			                + in[i+pulse_offsets[1]]
			                + in[i+pulse_offsets[2]]
			                + in[i+pulse_offsets[3]]) / 4.0;

			float space_threshold = inavg[i] + (avgpeak - inavg[i])/d_threshold;
			bool valid_preamble = true; //f'in c++
			for( int j=1.5*d_samples_per_symbol; j<=3*d_samples_per_symbol; j++)
				if(in[i+j] > space_threshold) valid_preamble = false;
			for( int j=5*d_samples_per_symbol; j<=7.5*d_samples_per_symbol; j++)
				if(in[i+j] > space_threshold) valid_preamble = false;
			if(!valid_preamble) continue;

			//be sure we've got enough room in the input buffer to copy out a whole packet
			if(ninputs-i < 240*d_samples_per_chip) {
				consume_each(i-1);
				return 0;
			}

			//all right i'm prepared to call this a preamble			
			//let's integrate and dump the output
			//FIXME: disable and use center sample
			bool life_sucks = true;
			if(life_sucks) {
				for(int j=0; j<240; j++) {
					out[j] = in[i+j*d_samples_per_chip];
				}
			} else {
				i -= d_samples_per_chip-1;
				integrate_and_dump(out, &in[i], 240, d_samples_per_chip);
			}

			//now tag the preamble
			add_item_tag(0, //stream ID
					 nitems_written(0), //sample
					 d_key,      //frame_info
			         pmt::pmt_from_double((double) space_threshold),
			         d_me        //block src id
			        );
			//std::cout << "PREAMBLE" << std::endl;
			
			//produce only one output per work call
			consume_each(i+240*d_samples_per_chip);
			return 240;
		}
	}
	
	//didn't get anything this time
	consume_each(ninputs);
	return 0;
}
