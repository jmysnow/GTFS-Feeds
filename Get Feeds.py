#!/usr/bin/env python
# coding: utf-8

# Mengying Ju 
# May 29, 2020

''' 
ATTENTION:
1. There is no data file needed so you can put the .py file in the folder where you want to get the feeds downloaded.
2. Make sure that you have a GTFS API, which can be obtained here. Once you have your API, please replace line 17 with your own API key.
http://transitfeeds.com/api/
3. Make sure you know your interest area, interest carriers and interest study period.
4. Make sure your have packages to be imported in this script installed (pandas, requests, os, shutil, datetime, zipfile)
5. Important parameters are to be set here.
'''
city = "San Francisco" # Replace the string with the name of your interest city
apikey = "yourkey" # Replace the string with your own GTFS API key
carriers = ['Caltrain', 'Muni', 'BART'] # Replace the list with a bunch of carriers that you are looking for

# Replace the following datetimes with the start and end date of your study period
from datetime import datetime
start = datetime(2020, 1, 6)
end = datetime(2020, 2, 28)


# In[1]:


import pandas as pd
import requests
import os
import shutil

from zipfile import ZipFile

from IPython.core.interactiveshell import InteractiveShell
InteractiveShell.ast_node_interactivity = "all"


# In[2]:


'''A class that helps search for the GTFS feeds'''
class GTFSapi(object):
    
    '''Initialize the object using a given API key'''
    def __init__(self, api_key):
        self.base_url = 'https://api.transitfeeds.com/v1/'
        self.api = '?key={}'.format(api_key)
        self.path = ''
        self.param_str = ''
        
    
    @property
    def full_url(self):
        """ Returns the full URL for requesting the data. """
        return '{}{}{}{}'.format(self.base_url, self.path, self.api, self.param_str)
    
    
    def get_request(self):
        """ Requests the API endpoint and returns the response """
        headers = {'content-type': 'application/json'}
        resp = requests.get(self.full_url, headers=headers)
        return resp.json()
    
    def get_locations(self):
        '''Gets a list of locations'''
        self.path = 'getLocations'
        resp = self.get_request()
        return resp
    
    def get_feeds(self, city_name, descendants = 1, page = 1, limit = 100, _type = 'gtfs', carrier = []):
        '''Gets the feeds of a given city with given carriers'''
        
        city_id = None
        result = self.get_locations()
        for record in result.get("results")['locations']:
            if record['n'] == city_name:
                city_id = record['id']
        search_str = '&location={}&descendants={}&page={}&limit={}&type={}'
        self.param_str = search_str.format(city_id, descendants, page, limit, _type)
        self.path = 'getFeeds'
        resp = self.get_request()
        
        to_return = []
        for record in resp['results']['feeds']:
            if record['t'][:-5] in carrier:
                to_return.append(record['id'])

        return to_return
    
    def get_feed_versions(self, feed_id, page = 1, limit = 100, err = 0, warn = 0):
        '''Gets the feeds with a specific feed version id'''
        
        self.path = 'getFeedVersions'
        search_str = '&feed={}&page={}&limit={}&err={}&warn={}'
        self.param_str = search_str.format(feed_id, page, limit, err, warn)
        resp = self.get_request()
        
        return resp
    
    def get_all_versions(self, feed_ids):
        '''
        Gets the feeds with a list of feed version ids.
        If total number of results exceeds the page limit,
        iteratively make requests until no results can be found.
        '''
        
        versions = []
        for _id in feed_ids:
            result = self.get_feed_versions(_id)
            vers = result['results']['versions']
            if result['results']['total'] > result['results']['limit']:
                queries = result['results']['total'] // result['results']['limit'] + 1
                for p in range(2, queries + 1):
                    vers.extend(self.get_feed_versions(_id, page = p)['results']['versions'])
            versions.extend(vers)
        return versions


# In[3]:


'''Initialize an instance for queries using your API key'''
feeds = GTFSapi(apikey)
feed_ids = feeds.get_feeds(city, carrier = carriers)

all_versions = feeds.get_all_versions(feed_ids)


# In[4]:


def filter_period(versions, start, end):
    '''
    Define a function that filters out the feeds within
    a specific study period:


    '''
    to_keep = []
    pairs = []
    flag = False
    for record in versions:
        s = datetime.strptime(record['d']['s'], '%Y%m%d')
        f = datetime.strptime(record['d']['f'], '%Y%m%d')
        if s <= start and f >= end:
            flag = True
        elif s >= start and f <= end:
            flag = True
        elif s <= start and f < end and f > start:
            flag = True
        elif s > start and s < end and f >= end:
            flag = True
        if flag and (s, f) not in pairs:
            pairs.append((s, f))
            to_keep.append(record)
        flag = False
        
    return to_keep


# In[5]:


def remove_all(_dir):
    '''
    Define a function that helps delete all files
    within a given directory.
    If there is any clustered subdirectory,
    recursively remove it.
    '''
    if not os.path.exists(_dir):
        return
    files = os.listdir(_dir)
    for f in files:
        if os.path.isdir(os.path.join(_dir, f)):
            remove_all(os.path.join(_dir, f))
            os.rmdir(os.path.join(_dir, f))
        else:
            os.remove(os.path.join(_dir, f))


# In[6]:


def download_join_feeds(feeds):
    '''
    Download the feeds within the study period,
    and save them with the IDs as filenames
    '''
    if not os.path.exists("Feeds"):
        os.makedirs("Feeds")
        
    for record in feeds:
        carrier = record['f']['t']
            
        filename = record['id'].replace("/", "_")
        url = record['url']
        r = requests.get(url)
        
        # Save the requested contents as zip files
        with open(os.path.join("Feeds", filename + '.zip'), 'wb') as f:
            f.write(r.content)         
            
        # Extract all files from the zip file
        zf = ZipFile(os.path.join("Feeds", filename + '.zip'), 'r')
        zf.extractall(os.path.join("Feeds", filename))
        zf.close()
        
        # Delete the zip file
        os.remove(os.path.join("Feeds", filename + '.zip'))
        
        # If there is another folder inside, move the files out
        files = os.listdir(os.path.join("Feeds", filename))
        if len(files) == 1 and os.path.isdir(os.path.join("Feeds", filename, files[0])):
            if files[0] != "__MACOSX":
                inner_files = os.listdir(os.path.join("Feeds", filename, files[0]))
                for f in inner_files:
                    _from = os.path.join("Feeds", filename, files[0], f)
                    _to = os.path.join("Feeds", filename, f)
                    shutil.move(_from, _to)
                os.rmdir(os.path.join("Feeds", filename, files[0]))
            
        # Join the tables and only keep the schedule information that we care about       
        calendar = pd.read_csv(os.path.join("Feeds", filename, "calendar.txt"), sep = ',')
        trips = pd.read_csv(os.path.join("Feeds", filename, "trips.txt"), sep = ',')
        stop_times = pd.read_csv(os.path.join("Feeds", filename, "stop_times.txt"), sep = ',')
        stops = pd.read_csv(os.path.join("Feeds", filename, "stops.txt"), sep = ',')
        
        # Make the IDs are in the same type 
        stop_times['stop_id'] = stop_times['stop_id'].astype(str)
        stops['stop_id'] = stops['stop_id'].astype(str)
        stop_times['trip_id'] = stop_times['trip_id'].astype(str)
        trips['trip_id'] = trips['trip_id'].astype(str)
        trips['service_id'] = trips['service_id'].astype(str)
        calendar['service_id'] = calendar['service_id'].astype(str)
        
        times = stop_times[['trip_id', 'arrival_time',
                    'departure_time', 'stop_id']].merge(stops[['stop_id', 'stop_name',
                                                   'stop_lat', 'stop_lon']], on='stop_id')
        times = times.merge(trips[['service_id', 'trip_id']], on = 'trip_id')
        times = times.merge(calendar[['service_id', 'start_date', 'end_date']], on = 'service_id')
        
        times.to_csv(os.path.join("Feeds", filename + '.csv'))
        
        # Delete the original folder because we don't need other redundant information
        # Uncomment the following two lines if you want to delete them, otherwise leave them commented       
        # remove_all(os.path.join("Feeds", filename))
        # os.rmdir(os.path.join("Feeds", filename))


# In[7]:

filtered = filter_period(all_versions, start, end)
download_join_feeds(filtered)


# In[ ]:




