#! /usr/bin/env python

import time
import requests
import json

API_KEY = "48067c9f84a8a54470a9892e7e49e0c8"

def req_get(session, url, params):
    """Make an HTTP GET request using the requests library"""
    try:
        r = session.get(url, params=params)

        # Check if any error was raised
        r.raise_for_status()
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        print e
        return None


    # TMDb imposes a rate limit of 40 requests for every 10 seconds. Sleep for
    # 0.25 seconds after every request so that we don't exceed our API limits
    time.sleep(0.25)

    return r

def get_reviews(session, movie_id, page):
    """Get movie reviews for a given movie ID."""
    # https://developers.themoviedb.org/3/movies/get-movie-reviews

    params = {"api_key": API_KEY, "language": "en-US", "page": page}
    r = req_get(session, "https://api.themoviedb.org/3/movie/%s/reviews" % movie_id,
                params=params)
    if r == None:
        return None
    return json.loads(r.content)

def save_json_to_file(filename, json_results):
    """Save our JSON results to a file"""
    with open(filename, "w") as output_file:
        json.dump(json_results, output_file,
                  sort_keys=True, indent=4)

def fetch_reviews(movie_input_file):
    """Fetch movie reviews information for the given input file of movies."""
    movie_input_text = open(movie_input_file, "r").read()
    movies = json.loads(movie_input_text)

    # Start an HTTP session to avoid TCP connection setup overhead each time we
    # send a request
    session = requests.Session()

    review_results = []
    count = 1
    # Fetch actors list for each movie
    for movie in movies:
        movie_id = movie["id"]
        movie_tmdb_id = movie["tmdb_id"]
        reviews = get_reviews(session, movie_tmdb_id, 1)
        if reviews == None:
            continue

        print "Fetched reviews: %s" % movie["name"]
        #print "Have %d pages"  % reviews["total_pages"]
        print "Have %d results"  % reviews["total_results"]
        if reviews["total_results"] == 0:
            continue

        for page in range(reviews["total_pages"]):
            reviews = get_reviews(session, movie_tmdb_id, page + 1)
            for review in reviews["results"]:
                saved_review = {
                    "movie_id": movie_id,
                    "id": count,
                    "author": review["author"],
                    "content": review["content"]
                }
                review_results += [saved_review]

                if len(review_results) % 100 == 0:
                    print "FINISHED: %d" % len(review_results)
                count += 1
    print "TOTAL REVIEWS: %d" % len(review_results)
    save_json_to_file("reviews.json", review_results)


if __name__ == '__main__':
    fetch_reviews("movies.json")
