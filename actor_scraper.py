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

def get_actors(session, movie_id):
    """Get the names of all actors who acted in a given movie ID."""
    # https://developers.themoviedb.org/3/movies/get-movie-credits

    params = {"api_key": API_KEY, "language": "en-US"}
    r = req_get(session, "https://api.themoviedb.org/3/movie/%s/credits" % movie_id,
                params=params)

    return json.loads(r.content)

def save_json_to_file(filename, json_results):
    """Save our JSON results to a file"""
    with open(filename, "w") as output_file:
        json.dump(json_results, output_file,
                  sort_keys=True, indent=4)

def fetch_actors(movie_input_file):
    """Fetch actor information for the given input file of movies."""
    movie_input_text = open(movie_input_file, "r").read()
    movies = json.loads(movie_input_text)

    # Start an HTTP session to avoid TCP connection setup overhead each time we
    # send a request
    session = requests.Session()

    actor_results = []
    # Fetch actors list for each movie
    for movie in movies:
        movie_id = movie["tmdb_id"]
        actors = get_actors(session, movie_id)["cast"]

        print "Fetched actors: %s" % movie["name"]

        for actor in actors:
            actor = {
                "tmdb_movie_id": movie["id"],
                "tmdb_actor_id": actor["id"],
                "name": actor["name"],
                "gender": actor["gender"]
            }
            actor_results += [actor]

            if len(actor_results) % 100 == 0:
                print "FINISHED: %d" % len(actor_results)

    save_json_to_file("actors.json", actor_results)

if __name__ == '__main__':
    fetch_actors("movies.json")
