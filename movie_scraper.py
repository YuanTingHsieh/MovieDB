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

def get_movie_director(session, movie_id):
    """Get the director name for a given movie ID using the GET credits API"""

    params = {"api_key": API_KEY}
    url = "https://api.themoviedb.org/3/movie/%s/credits" % movie_id
    r = req_get(session, url, params=params)

    # Parse the credits returned for the movie
    credits = json.loads(r.content)
    directors = []

    # Iterate over crew members listed in the movie credits
    for crew_member in credits["crew"]:
        if crew_member["job"] == "Director":
            # XXX: We assume that there is only one director
            return crew_member["name"], crew_member["id"]

    return None, None

def get_movie_details(session, movie_id):
    """Get movie details for a given movie ID. This will return details like
    movie runtime (mins), release date, overview etc."""

    params = {"api_key": API_KEY, "language": "en-US"}
    r = req_get(session, "https://api.themoviedb.org/3/movie/%s" % movie_id,
                params=params)

    return json.loads(r.content)

def discover_movies(session, release_year_gte, page):
    """Returns movies released after a given year in a page-by-page manner.
    Uses the TMDb movie discover API."""

    params = {"api_key": API_KEY,
              "primary_release_year.gte": release_year_gte,
              "page": page,
              "language": "en-US",
              "include_adult": "false",
              "include_video": "false"}

    r = req_get(session, "https://api.themoviedb.org/3/discover/movie",
                params=params)
    return json.loads(r.content)

def get_director_details(session, person_id):
    """Returns details of the director using the Person API."""

    params = {"api_key": API_KEY, "language": "en-US"}
    r = req_get(session, "https://api.themoviedb.org/3/person/%s" % person_id,
                params=params)
    return json.loads(r.content)

def save_json_to_file(filename, json_results):
    """Save our JSON results to a file"""
    with open(filename, "w") as output_file:
        json.dump(json_results, output_file,
                  sort_keys=True, indent=4)

def discover_all_movies(release_year_gte, num_pages):
    """Generates our Flask movie database by fetching movies released after a
    given year and fetches as many pages as requested."""

    saved_results = []
    saved_directors = []
    counter = 1
    director_counter = 1

    director_done = {}

    # Start an HTTP session to avoid TCP connection setup overhead each time we
    # send a request
    session = requests.Session()

    # The discover API returns one page of results. Call it in a loop for as
    # many pages as you need
    for page_num in xrange(1, num_pages+1):
        # Get a page full of movies released after the given year
        results = discover_movies(session, release_year_gte, page_num)

        for movie in results["results"]:
            # Fetch movie details for the selected movie
            movie_details = get_movie_details(session, movie["id"])

            # Get the name of the director
            director_name, director_tmdb_id = get_movie_director(session, movie["id"])
            if director_tmdb_id is not None and director_tmdb_id not in director_done:
                director_id = director_counter
            elif director_tmdb_id is not None and director_tmdb_id in director_done:
                director_id = director_done[director_tmdb_id]
            else:
                director_id = None

            print "Fetched: %s" % movie_details["original_title"]

            # Generate JSON object for our Flask database with the necessary
            # details
            saved_movie_details = {
                "id": counter,
                "tmdb_id": movie_details["id"],
                "name": movie_details["original_title"],
                "release_date": movie_details["release_date"],
                "director_name": director_name,
                "director_tmdb_id": director_tmdb_id,
                "director_id": director_id,
                "runtime": movie_details["runtime"],
                "overview": movie_details["overview"],
                "img_src": movie_details["backdrop_path"],
            }
            # Add JSON object to our results
            saved_results += [saved_movie_details]
            counter += 1

            # Check if director info is present
            if director_tmdb_id is None or director_tmdb_id in director_done:
                continue

            director_details = get_director_details(session, director_tmdb_id)
            saved_director_details = {
                "id": director_counter,
                "tmdb_id": director_tmdb_id,
                "name": director_details["name"],
                "birthday": director_details.get("birthday", ""),
                "gender": director_details["gender"],
                "biography": director_details["biography"],
            }

            saved_directors += [saved_director_details]
            director_done[director_tmdb_id] = director_counter
            director_counter += 1


        if len(saved_results) % 100 == 0:
            print "FINISHED: %d" % len(saved_results)

    # Save the generated results to a file
    save_json_to_file("movies.json", saved_results)
    save_json_to_file("directors.json", saved_directors)

if __name__ == '__main__':
    discover_all_movies(2005, 550)

