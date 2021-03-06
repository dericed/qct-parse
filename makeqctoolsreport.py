#!/usr/bin/env python
#makeqctoolsreport.py v 0.2.0

import os
import subprocess
import sys
import re
import gzip
import shutil
from distutils import spawn

#check to see that we have the required software to run this script
def dependencies():
	depends = ['ffmpeg','ffprobe']
	for d in depends:
		if spawn.find_executable(d) is None:
			print "Buddy, you gotta install " + d
			sys.exit()
	return

def parseInput():
	#print ffprobe output to txt file, we'll grep it later to see if we need to transcode for j2k/mxf
	ffdata = open(startObj + ".ffdata.txt","w")
	subprocess.call(['ffprobe','-show_streams','-of','flat','-sexagesimal','-i',startObj], stdout=ffdata)
	ffdata.close()

	#find which stream is the video stream
	ffdata = open(startObj + ".ffdata.txt","r")
	for line in ffdata:
		#find the line for video stream
		if re.search('.codec_type=\"video\"', line):
			#separate that line by periods, the formatting provided by ffprobe
			foolist = re.split(r'\.', line)
			#3rd part of that list is the video stream
			whichStreamVid = foolist[2]
	ffdata.close()

	#based on the vid stream we found, find the codec
	ffdata = open(startObj + ".ffdata.txt","r")
	for line in ffdata:
		if re.search('streams.stream.' + whichStreamVid + '.codec_name=', line):
			#dunno why we gotta remove quotes twice but there ya go
			[f[1:-1] for f in re.findall('".+?"', line)]
			codecName = f[1:-1]
	ffdata.close()
	os.remove(startObj + ".ffdata.txt") #only takes a string so cant send ffdata var idk

	#set some special strings to handle j2k/mxf files
	if codecName == 'jpeg2000':
		inputCodec = ' -vcodec libopenjpeg '
		filterstring = ' -vf tinterlace=mode=merge,setfield=bff '
	else:
		inputCodec = ' '
		filterstring = ' '
	return inputCodec, filterstring


def transcode():
	#transcode to .nut	
  
	ffmpegstring = ['ffmpeg'] 
	if not inputCodec == ' ':
		ffmpegstring.append(inputCodec)
	ffmpegstring.extend(['-vsync','0','-i',startObj,'-vcodec','rawvideo','-acodec','pcm_s24le'])
	if not filterstring== ' ':
		ffmpegstring.append(inputCodec)
	ffmpegstring.extend(['-f','nut','-y',startObj + '%s' % '.temp1.nut'])
	subprocess.call(ffmpegstring)

	
def get_audio_stream_count():
	audio_stream_count = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index','-of', 'flat', sys.argv[1]]).splitlines()
	return len(audio_stream_count)
	
	
def makeReport():
	#here's where we use ffprobe to make the qctools report in regular xml
	print "writing ffprobe output to xml"
	audio_tracks = get_audio_stream_count()
	if audio_tracks > 0:
		ffprobe_command = ['ffprobe','-loglevel','error','-f','lavfi','-i','movie=' + startObj + ':s=v+a[in0][in1],[in0]signalstats=stat=tout+vrep+brng,cropdetect=reset=1,split[a][b];[a]field=top[a1];[b]field=bottom[b1],[a1][b1]psnr[out0];[in1]ebur128=metadata=1[out1]','-show_frames','-show_versions','-of','xml=x=1:q=1','-noprivate']
	elif audio_tracks == 0:
		ffprobe_command = ['ffprobe','-loglevel','error','-f','lavfi','-i','movie=' + startObj + ',signalstats=stat=tout+vrep+brng,cropdetect=reset=1,split[a][b];[a]field=top[a1];[b]field=bottom[b1],[a1][b1]psnr','-show_frames','-show_versions','-of','xml=x=1:q=1','-noprivate']
	
	tmpxml = open(startObj + '.qctools.xml','w')
	subprocess.call(ffprobe_command, stdout=tmpxml)
	tmpxml.close()

	#gzip that tmpxml file then delete the regular xml file cause we dont need it anymore
	print "gzip-ing ffprobe xml output"
	with open(startObj + '.qctools.xml', 'rb') as f_in, gzip.open(startObj + '.qctools.xml.gz','wb') as f_out:
		shutil.copyfileobj(f_in,f_out)
	os.remove(startObj + '.qctools.xml')
	if os.path.exists(startObj + '.temp1.nut'):
		os.remove(startObj + '.temp1.nut')


dependencies()
startObj = sys.argv[1]
startObj = startObj.replace("\\","/")
inputCodec, filterstring = parseInput()
if 'jpeg' in inputCodec:
	transcode()
	startObj = startObj + ".temp1.nut"
makeReport()
