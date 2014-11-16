from __future__ import print_function

__author__ = 'deathbots'

"""
gets raw song lyrics from chartlyrics.com
supply a search term, get raw data on command line
"""

import sys
import argparse
import urllib
import urllib2
import xml.etree.ElementTree as et
import socket

def errout(*out):
    print("Lyrics Fetch Error: ", *out, file=sys.stderr)

def string_from_url(url_string):
    """
    Returns string data retrieved at URL
    :param url_string: url string
    :return: string contents of data at URL
    """
    try:
        u = urllib2.urlopen(url_string)
    except urllib2.HTTPError, e:
        errout("HTTP Error code: {0}".format(e.code))
        raise
    except socket.error, e:
        errout("Socket Error, Error message: {0}".format(e.strerror))
        raise
    try:
        data = u.read()
    except Exception as e:
        errout("No data from URL, error: {0}".format(e.message))
        raise

    return data


class ParsedLyrics(object):
  __slots__ = ["song_title", "lyric_line_count", "raw_lines"]
  def __init__(self, song_title, lyric_line_count, raw_lines):
     self.song_title = song_title
     self.lyric_line_count = lyric_line_count
     self.raw_lines = raw_lines
  def __repr__(self):
    return "<ParsedLyric song_title:{0} lyric_line_count:{1} \nraw_lines:\n {2}\n>".format(self.song_title, self.lyric_line_count,self.raw_lines)

class LyricSearchResult(object):
  __slots__ = ["artist", "song_title", "lyrics_url"]
  def __init__(self, artist, song_title, lyrics_url):
     self.artist = artist
     self.song_title = song_title
     self.lyrics_url = lyrics_url
  def __repr__(self):
    return "<LyricSearchResult artist:{0} song_title:{1} lyrics_url:{2}>".format(self.artist, self.song_title, self.lyrics_url)


def lyric_html_to_parsedlyrics(lyric_html):
    """
    Translates a specific web page of lyric data to raw lines
    :param lyric_html: string data of html from lyrics page
                at http://api.chartlyrics.com/apiv1.asmx/SearchLyricText?lyricText=dark%20side%20of%20the%20moon
    :return a ParsedLyrics object which contains the raw data and data about it
    """
    import re
    lyric_start_re = '.*title="(.*)" />'
    lyric_line_re = '(.*)<br />'
    lyric_end1_re = '</p>.*'
    lyric_end2_re = '.*<div id="adlyric">.*'

    # creates cleanly printable data
    # from the chartlyrics.com page
    found_flag = False
    done_flag = False
    lyric_line_count = 0
    lines = ""
    song_title = ""
    for line in lyric_html.splitlines():
        # lyric start line looks like
        # alt="" title="Pink Floyd Brain Damage" />
        if found_flag and not done_flag:
            #print("---------------------found--------------------")
            # if we have found a lyric start marker, the next line
            # should begin lyrics
            ll = re.match(lyric_line_re,line)
            if ll:
                lyric_line = ll.group(1).replace("<br />","\n").strip(' ')
                lines = "{0}\n{1}".format(lines,lyric_line)
                lyric_line_count = lyric_line_count + 1

        ls = re.match(lyric_start_re,line)
        if ls:
            song_title = ls.group(1)
            found_flag = True
        d1 = re.match(lyric_end1_re,line)
        d2 = re.match(lyric_end2_re,line)
        if d1 or d2:
            #print("---------------------done--------------------")
            done_flag = True

    return ParsedLyrics(song_title,lyric_line_count,lines)


def validate_process(lyric_obj, min_lines):
    if lyric_obj.lyric_line_count >= min_lines:
        return True
    print("Required: at least {0} lyric lines".format(min_lines))
    print("Found: {0} lyrics lines".format(lyric_obj.lyric_line_count))
    return False


def parse_args():

    parser = argparse.ArgumentParser(description='Search chartlyrics.com for text and receive raw lyrics string back')

    parser.add_argument('-s','--searchterm', help='lyric text to search for', required=True)
    parser.add_argument('-l','--minlines', help='safeguard for minimum expected lyric lines', type=int, required=True)
    args = vars(parser.parse_args())

    return args


def get_namespaced_tag(ns,tag):
    return str( et.QName( ns, tag))


def get_top_search_result_from_soap(soap_text):
    """
    Parses xml text output of search results - returns an object
    which describes the top resulting artist, song title, and url for lyrics

    :param soap_text: xml data form chartlyrics.com
        like
          <ArrayOfSearchLyricResult xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns="http://api.chartlyrics.com/">          <SearchLyricResult>
              <SearchLyricResult>
                <TrackId>0</TrackId>
                <LyricChecksum>50364d8d6571621a98a85681fece985b</LyricChecksum>
                <LyricId>635</LyricId>
                <SongUrl>http://www.chartlyrics.com/mBjZg2N310ewO7khMjdcRw/Brain+Damage.aspx</SongUrl>
                <ArtistUrl>http://www.chartlyrics.com/mBjZg2N310ewO7khMjdcRw.aspx</ArtistUrl>
                <Artist>Pink Floyd</Artist>
                <Song>Brain Damage</Song>
                <SongRank>9</SongRank>
              </SearchLyricResult>
    """
    blankresult = LyricSearchResult("","","")
    ns = 'http://api.chartlyrics.com/'
    slr_tag = get_namespaced_tag(ns,'SearchLyricResult')
    url_tag = get_namespaced_tag(ns,'SongUrl')
    artist_tag = get_namespaced_tag(ns,'Artist')
    song_tag = get_namespaced_tag(ns,'Song')

    element = et.fromstring(soap_text)
    top_result = element.find(slr_tag)
    # print(et.dump(top_result))

    top_song_urls = top_result.findall(url_tag)
    if not len(top_song_urls) > 0:
        errout("Could not determine URL of top search result")
        return blankresult
    top_song_url = top_song_urls[0].text

    top_artists = top_result.findall(artist_tag)
    if not len(top_artists) > 0:
        errout("Could not determine artist of top search result")
        return blankresult
    top_artist = top_artists[0].text

    top_song_titles = top_result.findall(song_tag)
    if not len(top_song_titles) > 0:
        errout("Could not determine song title of top search result")
        return blankresult
    top_song_title = top_song_titles[0].text

    return LyricSearchResult(top_artist,top_song_title,top_song_url)

def main():
    args = parse_args()
    search_term = args['searchterm']
    search_to_encode = { 'LyricText' : search_term }
    search_term = urllib.urlencode(search_to_encode)
    min_lines = args['minlines']

    api_url = 'http://api.chartlyrics.com/apiv1.asmx/SearchLyricText?'+search_term
    try:
        soap_data = string_from_url(api_url)
    except Exception as e:
        errout("Could not retrieve data from url {0}, error was: {1}".format(api_url,e.strerror))
        exit(1)
    lyrics_search_result = get_top_search_result_from_soap(soap_data)
    found_artist = lyrics_search_result.artist
    found_song_title = lyrics_search_result.song_title
    found_lyrics_url = lyrics_search_result.lyrics_url
    lyrics_obj = lyric_html_to_parsedlyrics(string_from_url(found_lyrics_url))
    if validate_process(lyrics_obj,min_lines):
        print("Artist: {0}\nSong: {1}.".format(found_artist,found_song_title))
        print(lyrics_obj.raw_lines)


if __name__ == "__main__":
    main()
