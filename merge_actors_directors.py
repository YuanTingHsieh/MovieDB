#! /usr/bin/env python

import json

def save_json_to_file(filename, json_results):
    """Save our JSON results to a file"""
    with open(filename, "w") as output_file:
        json.dump(json_results, output_file,
                  sort_keys=True, indent=4)

def main():
    actors_input_text = open("actors_splitted.json", "r").read()
    actors = json.loads(actors_input_text)
    directors_input_text = open("directors.json", "r").read()
    directors = json.loads(directors_input_text)
    acted_input_text = open("acted_deduplicated.json", "r").read()
    acted = json.loads(acted_input_text)

    # We will have directors IDs starting from 1 to len(directors). 
    # Actors will have IDs starting from len(directors) + 1. We just need to
    # increment each actor's ID by len(directors)
    increment = len(directors)

    done = {}
    director = {}
    contributors = []
    contributors.extend(directors)
    for director in directors:
        done[director["tmdb_id"]] = director["id"]

    for actor in actors:
        if actor["tmdb_id"] in done:
            # Some actors are directors too. Don't readd them to contributors
            director[actor["id"]] = done[actor["tmdb_id"]]
            continue
        actor["id"] += increment
        contributors += [actor]

    acting = []
    for actor_playing in acted:
        old_actor_id = actor_playing["actor_id"] - increment
        if old_actor_id in director:
            actor_playing["actor_id"] = director[old_actor_id]
        acting += [actor_playing]

    save_json_to_file("contributors.json", contributors)
    save_json_to_file("acted_deduplicated_new.json", acting)

if __name__ == '__main__':
    main()
