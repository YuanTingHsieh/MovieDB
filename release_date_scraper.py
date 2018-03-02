#! /usr/bin/env python

import time
import requests
import json

API_KEY = "48067c9f84a8a54470a9892e7e49e0c8"

def req_get(session, url, params):
    """Make an HTTP GET request using the requests library"""
    r = session.get(url, params=params)

    # Check if any error was raised
    r.raise_for_status()

    # TMDb imposes a rate limit of 40 requests for every 10 seconds. Sleep for
    # 0.25 seconds after every request so that we don't exceed our API limits
    time.sleep(0.25)

    return r

def get_release_dates(session, movie_id):
    """Get movie reviews for a given movie ID."""
    # https://developers.themoviedb.org/3/movies/get-movie-reviews

    params = {"api_key": API_KEY, "language": "en-US"}
    r = req_get(session, "https://api.themoviedb.org/3/movie/%s/release_dates" % movie_id,
                params=params)
    return json.loads(r.content)

def save_json_to_file(filename, json_results):
    """Save our JSON results to a file"""
    with open(filename, "w") as output_file:
        json.dump(json_results, output_file,
                  sort_keys=True, indent=4)

def fetch_reviews(movie_input_file):
    """Fetch movie release dates information for the given input file of movies."""
    movie_input_text = open(movie_input_file, "r").read()
    movies = json.loads(movie_input_text)

    # Start an HTTP session to avoid TCP connection setup overhead each time we
    # send a request
    session = requests.Session()

    release_dates_results = []
    # Fetch actors list for each movie
    for movie in movies:
        movie_id = movie["tmdb_id"]
        try:
            release_dates = get_release_dates(session, movie_id)["results"]

            print "Fetched release dates: %s" % movie["name"]

            for release_date in release_dates:

                saved_release_date = {
                    "movie_id": movie["id"],
                    "country": release_date["iso_3166_1"],
                    "certification": release_date["release_dates"][0]["certification"],
                    "release_date": release_date["release_dates"][0]["release_date"]
                }
                release_dates_results += [saved_release_date]

                if len(release_dates_results) % 100 == 0:
                    print "FINISHED: %d" % len(release_dates_results)
        except:
            print "movie %s NOT FOUND" %movie["name"]

    save_json_to_file("release_dates.json", release_dates_results)


if __name__ == '__main__':
    fetch_reviews("movies.json")
