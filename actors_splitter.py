import json


def save_json_to_file(filename, json_results):
    """Save our JSON results to a file"""
    with open(filename, "w") as output_file:
        json.dump(json_results, output_file,
                  sort_keys=True, indent=4)

def split_actors(actors_input_file, movies_input_file):
    actors_input_text = open(actors_input_file, "r").read()
    movies_input_text = open(movies_input_file, "r").read()

    movies_file = json.loads(movies_input_text)
    actors_file = json.loads(actors_input_text)

    actors_list = []
    acted_list = []

    actor_tmdb_ids = {0}
    actor_id_pairs = {}
    movies_id_pairs = {}

    count = 0
    total = len(actors_file)

    for movie in movies_file:
        movies_id_pairs.update({movie["tmdb_id"]: movie["id"]})


    for actor in actors_file:
        if (count % 1000 == 0):
            print "In %ith iteration, %%%i DONE" %(count, (count*100/total))

        movie_id = actor["movie_id"]
        actor_id = 0

        del actor["movie_id"]
        if (actor["tmdb_id"] not in actor_tmdb_ids):
            actor_tmdb_ids.add(actor["tmdb_id"])
            actor_id = count + 1
            actor_id_pairs.update({actor["tmdb_id"]: actor_id})
            actor.update({"id": actor_id})
            actors_list += [actor]
        else:
            actor_id = actor_id_pairs[actor["tmdb_id"]]

        try:
            acted = {
                "movie_id": movies_id_pairs[movie_id],
                "actor_id": actor_id
            }
            acted_list += [acted]
        except:
            pass
        count += 1

    # save_json_to_file("acted.json", acted_list)
    save_json_to_file("actors_splitted.json", actors_list)



if __name__ == '__main__':
    split_actors("actors+acted.json", "movies.json")
