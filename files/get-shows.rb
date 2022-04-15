# Ruby file to get the shows from Internet into Downloget

require 'net/http'
require 'json'


shows = {
			'6music recommends' => 'https://www.bbc.co.uk/programmes/b00rz79k/episodes/player?page='
		}
		# 'Mark Riley' => 'https://www.bbc.co.uk/programmes/b00c72y1/episodes/player?page='
		# 'Music Planet' => 'https://www.bbc.co.uk/programmes/b09ymx3v/episodes/player?page=',
			# 'Mark Riley' => 'https://www.bbc.co.uk/programmes/b00c72y1/episodes/player?page='
		#		  'Geoff Smith Jazz' => 'http://www.bbc.co.uk/programmes/b01h5z0s/episodes/player'}   b0072lb2
		# 'Tom_Ravenscroft2' => 'https://www.bbc.co.uk/programmes/b00slvl3/episodes/player?page=',
# 		 'Gideon Coe' => 'http://www.bbc.co.uk/programmes/b0072l9v/episodes/player',
# 'Steve Lamacq' => 'https://www.bbc.co.uk/programmes/b0072lb2/episodes/player?page=',

#$dirroot = '/media/pi/SANDISK-PI/music/radio'
#TARGET = '/mnt/usb/music/radio/'
#TARGET = '~/radio_data/'
# TARGET = '/home/colin999_gmail_com/radio_data/'
TARGET = '/radio_data/'

#TEMP = '/tmp/'
TEMP = '/tmp/'

$new_files = 0


def DaysAgo (d) 
	Time.now - d*24*60*60
end

# Set the track number such that recent dates have the lowest number
def SetTrack (dir)
	#	endDate = Time.new(2026,12,1)  #2478
	endDate = Time.new(2044,12,1)  #2478
	Dir.glob(dir + '/20*-*-*.m4a').each do |f|
		fb = File.basename(f)
		tnum = ((endDate - Time.new(fb[0,4],fb[5,2],fb[8,2]))/(24*60*60)).to_i
		tnum2 = (tnum % 990) + 1
		disk = ((tnum - tnum2)/990) + 1

		bits = fb.split('~')
		# puts "split: #{bits[1]}"
		artist = "0BBC6music"
		album = "0BBC6-" + bits[1]
		title = bits[0] + "-" + bits[1] + "-" + bits[2]

		docom = 'AtomicParsley ' + f + ' --freefree --overWrite --disk ' + disk.to_s + ' --tracknum ' + tnum2.to_s + \
			' --artist ' + artist + ' --albumArtist ' + artist + ' --title ' + title + ' --album ' + album
		# docom = 'AtomicParsley ' + f + ' --freefree --overWrite --disk ' + disk.to_s + ' --tracknum ' + tnum2.to_s
		puts docom
		system docom
	end
end
		

def ShowsOnPage(uri, daysDownload)
	response = Net::HTTP.get_response(uri)

		#puts response
#1		response.body.scan( /data-pid="([^"]*)".*?property="startDate".*? content="([^T]*?)T/m).each do | pid |
#	response.body.scan( /property="startDate".*? content="([^T]*?)T.*?data-pid="([^"]*)"/m).each do | pid |
#response.body.scan( /<li>.*?property="startDate".*? content="([^T]*?)T.*?data-pid="([^"]*)"(.*?)<\/li>/m).each do | pid |
#"RadioEpisode","identifier":"m000bp6g","episodeNumber":null,"description":"Say Sue Me, Sparkling and Berries in the mix as Lammo picks his favourite new tunes.","datePublished":"2019-11-29",
	response.body.scan( /RadioEpisode","identifier":"([^"]*)".*?"datePublished":"([^"]*)"/m).each do | pid |
		pids = pid[0]
		fb = pid[1]
		puts "NEW pid,date: #{pids} #{fb}"
#		if (pid[2].include? 'property="uploadDate"')
		if (1 == 1)

					# What year and month is it?
			today = Time.new.to_s
			if (fb <= today)
				puts "pids:" + pids
				puts "pids:" + pids + " time: " + fb
				if (Time.new(fb[0,4],fb[5,2],fb[8,2]) > DaysAgo(daysDownload))
					puts "Fetching show: " + pids + " " + fb
					files = Dir.glob(TARGET + '*~' + pids + '.m4a')
					if (files.count == 0) 

						# # Is the USB disk mounted properly?
						# if (!File.exist?(TARGET[0..-2]))
						# 	abort ("***** Looks like USB not mounted **********")
						# end


						docom = 'get_iplayer --force --output "' + TEMP + '"  --file-prefix="<firstbcastdate>~<nameshort>~<episode>~<pid>" --type=radio --radio-quality="std,med" --pid=' + \
							pids + ''
							# docom = 'get_iplayer --force --output "' + TEMP + '"  --file-prefix="<firstbcastdate>~<nameshort>~<episode>~<pid>~" --type=radio --pid=' + \
							# pids + ' --albumArtist "0<nameshort>~<episode>" --artist="0<nameshort>~<episode>" --title="<firstbcastdate>~<nameshort>~<episode>"'
						#docom = thisdir + '/get_iplayer/perl get_iplayer.pl --output "x:\downloads"  --file-prefix="<firstbcastdate>_<nameshort>_<episode>_<pid>" --type=radio --aactomp3 --pid=' + pids
						puts docom
						system docom
						SetTrack TEMP
						system 'mv ' + TEMP + '*.m4a ' + TARGET
						#system 'cacls', 'x:\downloads\*_' + pids + '*.mp3',   '/E', '/G', 'everyone:R'
						$new_files += 1
					end
				else
					puts "Show too old: " + pids + " " + fb
				end
			else
				puts "Show in future (NEVER SEE THIS)" + pids + " " + fb
			end
		else
			puts "Show not uploaded yet or expired " + pids + " " + fb
		end
	end
end







# Only download shows broadcast in the last <daysDownload> days
# Delete files older than <daysDelete>
# daysDownload = 14
daysDownload = 5
daysDelete = daysDownload + 10
puts "*** get-shows  #{RUBY_VERSION}-p#{RUBY_PATCHLEVEL}"
thisdir = File.expand_path(File.dirname(__FILE__))
lockfile = TEMP + 'lock.txt'
# 2 hours ago
if (File.exist? lockfile )
	# If the lock is more than 2 hours old, just delete it
	if (File.ctime(lockfile) > Time.now - 2*60*60)
		abort ("Already running: " + lockfile)
	end
	File.delete lockfile
end
system 'date > ~/me/radio/lastrun'

# # Is the USB disk mounted properly?
# if (!File.exist?(TARGET[0..-2]))
# 	abort ("***** Looks like USB not mounted **********")
# end
	

File.new lockfile,"w"
#Dir.chdir(thisdir + "/get_iplayer")
begin
	shows.each do | name, url |
		puts name + " " + url

		# What year and month is it?
		today = Time.new.to_s
		iyear = today[0,4]
		imonth = today[5,2]
		uri = URI.parse(url + '1')
		puts uri
		# This month
		ShowsOnPage(uri, daysDownload)
		# Previous month
		uri = URI.parse(url + '2')
		puts uri
		ShowsOnPage(uri, daysDownload)
	end
	rescue => e 
		puts "***Error: " + e.message
		puts e.backtrace.join("\n")
	ensure
		File.delete lockfile
end


# Ruby to purge old radio files
tnum = 3650
Dir.glob(TARGET + '20*-*-*.m4a').each do |f|
	fb = File.basename(f)
			# 3 days spare
	if (Time.new(fb[0,4],fb[5,2],fb[8,2]) < DaysAgo(daysDelete))
		puts "delete " + f
		File.delete(f)
	else
		tnum = tnum + 1
	end
end

print("New files downloaded:", $new_files)
if ($new_files > 0)
	# Synch with Cloud Storage
	puts "NEED TO MOVE TO GOOGLE TODO sync " +  'gsutil -m rsync -d ' + TARGET +  ' gs://straview3.appspot.com/radio_data'
	# system 'gsutil -m rsync -d ' + TARGET +  ' gs://straview3.appspot.com/radio_data'

	# Get APP to move it into Google
	# uri = URI('https://straview3.appspot.com/syncradio')
	# response = Net::HTTP.get(uri)
	# JSON.parse(response)
end